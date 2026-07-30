"""Parse, validate, and modify ComfyUI workflow JSON."""

import copy
from dataclasses import dataclass, field


@dataclass
class ParamInfo:
    node_id: str
    param_name: str
    param_type: str
    current_value: any
    title: str = ""
    options: list[str] | None = None


@dataclass
class NodeSummary:
    node_id: str
    class_type: str
    title: str = ""


PRIMITIVE_TYPES = {"PrimitiveFloat": "float", "PrimitiveInt": "int", "PrimitiveString": "string"}
TEXT_NODE_TYPES = {"CLIPTextEncode", "CLIPTextEncodeSDXL"}


def extract_params(workflow: dict) -> list[ParamInfo]:
    params = []
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        title = node.get("_meta", {}).get("title", class_type)
        if class_type in PRIMITIVE_TYPES:
            param_type = PRIMITIVE_TYPES[class_type]
            value = inputs.get("value")
            params.append(ParamInfo(node_id=node_id, param_name=_title_to_param_name(title), param_type=param_type, current_value=value, title=title))
        elif class_type in TEXT_NODE_TYPES:
            text = inputs.get("text", "")
            is_negative = any(w in text.lower() for w in ("bad", "worst", "lowres", "ugly", "deformed", "negative"))
            param_name = "negative_prompt" if is_negative else "positive_prompt"
            params.append(ParamInfo(node_id=node_id, param_name=param_name, param_type="string", current_value=text, title=title))
        elif class_type == "CheckpointLoaderSimple":
            params.append(ParamInfo(node_id=node_id, param_name="model", param_type="choice", current_value=inputs.get("ckpt_name", ""), title=title, options=[]))
        elif class_type == "EmptyLatentImage":
            for key in ("width", "height", "batch_size"):
                if key in inputs:
                    params.append(ParamInfo(node_id=node_id, param_name=key, param_type="int", current_value=inputs[key], title=title))
        elif class_type == "KSampler":
            for key in ("seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"):
                if key in inputs:
                    val = inputs[key]
                    ptype = "int" if key in ("seed", "steps") else ("float" if key in ("cfg", "denoise") else "choice")
                    params.append(ParamInfo(node_id=node_id, param_name=key if key != "sampler_name" else "sampler", param_type=ptype, current_value=val, title=title))
    return params


def inject_params(workflow: dict, params: dict[str, any]) -> dict:
    wf = copy.deepcopy(workflow)
    wf = resolve_placeholders(wf, params)
    param_list = extract_params(wf)
    name_to_node = {p.param_name: (p.node_id, p.param_type) for p in param_list}
    for key, value in params.items():
        if key in wf:
            _inject_value(wf[key], value, key)
        elif key in name_to_node:
            node_id, _ = name_to_node[key]
            _inject_value(wf[node_id], value, key)
    return wf


def resolve_placeholders(workflow: dict, values: dict[str, any]) -> dict:
    INT_KEYS = {"seed", "steps", "width", "height", "batch_size", "control_after_generate"}
    FLOAT_KEYS = {"cfg", "denoise", "cfg_scale", "strength", "start_at_step", "end_at_step"}
    for node in workflow.values():
        inputs = node.get("inputs", {})
        for key, val in list(inputs.items()):
            if not isinstance(val, str):
                continue
            new_val = val
            for token, replacement in values.items():
                placeholder = f"%{token}%"
                if placeholder in new_val:
                    if new_val.strip() == placeholder:
                        if key.lower() in INT_KEYS:
                            new_val = int(replacement)
                        elif key.lower() in FLOAT_KEYS:
                            new_val = float(replacement)
                        else:
                            new_val = str(replacement)
                    else:
                        new_val = new_val.replace(placeholder, str(replacement))
            if new_val is not val:
                inputs[key] = new_val
    return workflow


def _inject_value(node: dict, value: any, key: str = ""):
    class_type = node.get("class_type", "")
    inputs = node.get("inputs", {})
    if class_type in PRIMITIVE_TYPES:
        if class_type == "PrimitiveInt":
            inputs["value"] = int(value)
        elif class_type == "PrimitiveFloat":
            inputs["value"] = float(value)
        elif class_type == "PrimitiveString":
            inputs["value"] = str(value)
    elif class_type in TEXT_NODE_TYPES:
        inputs["text"] = str(value)
    elif class_type == "CheckpointLoaderSimple":
        inputs["ckpt_name"] = str(value)
    elif class_type == "EmptyLatentImage":
        if isinstance(value, dict):
            inputs.update(value)
        else:
            if key in inputs:
                inputs[key] = int(value)
            else:
                for k in ("width", "height", "batch_size"):
                    if k in inputs:
                        inputs[k] = int(value)
                        break
    elif class_type == "KSampler":
        if isinstance(value, dict):
            for k, v in value.items():
                mapped = "sampler_name" if k == "sampler" else k
                if mapped in inputs:
                    if mapped in ("seed", "steps"):
                        inputs[mapped] = int(v)
                    elif mapped in ("cfg", "denoise"):
                        inputs[mapped] = float(v)
                    else:
                        inputs[mapped] = v
        else:
            mapped = "sampler_name" if key == "sampler" else key
            if mapped in inputs:
                if mapped in ("seed", "steps"):
                    inputs[mapped] = int(value)
                elif mapped in ("cfg", "denoise"):
                    inputs[mapped] = float(value)
                else:
                    inputs[mapped] = value


def list_nodes(workflow: dict) -> list[NodeSummary]:
    return [NodeSummary(node_id=nid, class_type=n.get("class_type", "unknown"), title=n.get("_meta", {}).get("title", n.get("class_type", ""))) for nid, n in workflow.items()]


def _normalize_workflow(workflow: dict) -> dict:
    first_val = next(iter(workflow.values()), None)
    if isinstance(first_val, dict) and "class_type" in first_val:
        return workflow
    if "nodes" in workflow and isinstance(workflow["nodes"], list):
        normalized = {}
        for n in workflow["nodes"]:
            nid = str(n.get("id", ""))
            normalized[nid] = {"class_type": n.get("type", ""), "inputs": {}, "_meta": {"title": n.get("title", n.get("type", ""))}}
            for inp in n.get("inputs", []):
                normalized[nid]["inputs"][inp.get("name", "")] = inp.get("link")
            if "widgets_values" in n:
                normalized[nid]["widgets_values"] = n["widgets_values"]
        return normalized
    return workflow


def _title_to_param_name(title: str) -> str:
    mappings = {"seed": "seed", "positive prompt": "positive_prompt", "negative prompt": "negative_prompt", "+prompt": "positive_prompt", "-prompt": "negative_prompt", "prompt": "prompt", "load checkpoint": "model", "latent image size": "resolution", "cfg": "cfg", "steps": "steps", "denoise": "denoise", "sample": "sampler", "width": "width", "height": "height"}
    title_lower = title.lower().strip()
    for key, value in mappings.items():
        if key in title_lower:
            return value
    return title_lower.replace(" ", "_").replace("-", "_")


@dataclass
class FixReport:
    missing: list[str]
    replaced: dict[str, str]
    unfixable: list[str]
    warning: str = ""


def _extract_signature(node_info: dict) -> dict[str, set]:
    sig = {"inputs": set(), "outputs": set()}
    for section in ("required", "optional"):
        for name, spec in node_info.get("input", {}).get(section, {}).items():
            if isinstance(spec, (list, tuple)) and len(spec) >= 1:
                type_val = spec[0]
                if isinstance(type_val, (list, tuple)):
                    type_val = type_val[0] if type_val else "UNKNOWN"
                if isinstance(type_val, str):
                    sig["inputs"].add(type_val)
            elif isinstance(spec, str):
                sig["inputs"].add(spec)
    output_info = node_info.get("output", {})
    if isinstance(output_info, list):
        for out_item in output_info:
            if isinstance(out_item, (list, tuple)) and len(out_item) >= 3:
                sig["outputs"].add(str(out_item[2]))
            elif isinstance(out_item, str):
                sig["outputs"].add(out_item)
    elif isinstance(output_info, dict):
        for out_list in output_info.values():
            if isinstance(out_list, list):
                for t in out_list:
                    if isinstance(t, str):
                        sig["outputs"].add(t)
    return sig


def _sig_similarity(a: dict[str, set], b: dict[str, set]) -> float:
    out_a, out_b = a["outputs"], b["outputs"]
    out_score = len(out_a & out_b) / len(out_a | out_b) if (out_a | out_b) else 0.5
    in_a, in_b = a["inputs"], b["inputs"]
    in_score = len(in_a & in_b) / len(in_a | in_b) if (in_a | in_b) else 0.5
    return out_score * 0.7 + in_score * 0.3


def check_missing_nodes(workflow: dict, available_object_info: dict) -> FixReport:
    workflow = _normalize_workflow(workflow)
    used_types = set()
    for node in workflow.values():
        ct = node.get("class_type", "")
        if ct:
            used_types.add(ct)
    available_set = set(available_object_info.keys())
    missing = sorted(used_types - available_set)
    if not missing:
        return FixReport(missing=[], replaced={}, unfixable=[], warning="All nodes available.")
    avail_sigs = {name: _extract_signature(info) for name, info in available_object_info.items()}
    replaced = {}
    unfixable = []
    curated = {"LoraLoader": ["Power Lora Loader (rgthree)", "CR LoRA Stack", "LoRA Stacker"], "LoRAStacker": ["Power Lora Loader (rgthree)", "LoraLoader"], "FaceDetailer": ["FaceRestoreCFWithModel", "ADetailer", "DetailerForYou"], "UltimateSDUpscale": ["IterativeUpscale", "UpscaleModelLoader+ImageUpscaleWithModel"], "IPAdapter": ["IPAdapterAdvanced", "IPAdapterUnifiedLoader"], "ControlNetLoader": ["ControlNetLoaderAdvanced", "ControlNetApply"], "HiresFix": ["UltimateSDUpscale", "KSampler (with latent upscale)"]}
    for mt in missing:
        found = False
        for pattern, candidates in curated.items():
            if pattern.lower() in mt.lower():
                for cand in candidates:
                    if cand in available_set:
                        replaced[mt] = cand
                        found = True
                        break
                if found:
                    break
        if not found:
            mt_parts = set(mt.lower().replace("_", " ").replace("-", " ").split())
            for at in available_set:
                at_parts = set(at.lower().replace("_", " ").replace("-", " ").split())
                overlap = mt_parts & at_parts
                if len(overlap) >= 2 and len(overlap) / max(len(mt_parts), 1) >= 0.4:
                    replaced[mt] = at
                    found = True
                    break
        if not found:
            unfixable.append(mt)
    return FixReport(missing=missing, replaced=replaced, unfixable=unfixable)


def auto_fix_workflow(workflow: dict, available_object_info: dict) -> tuple[dict, FixReport]:
    wf = copy.deepcopy(workflow)
    wf = _normalize_workflow(wf)
    report = check_missing_nodes(wf, available_object_info)
    if report.replaced:
        for node in wf.values():
            ct = node.get("class_type", "")
            if ct in report.replaced:
                node["class_type"] = report.replaced[ct]
                if "_meta" in node:
                    node["_meta"]["title"] = f"[auto] {report.replaced[ct]}"
    return wf, report