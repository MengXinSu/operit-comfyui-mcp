"""FastMCP server for operit-comfyui-mcp: full ComfyUI control."""

import json
import os
import asyncio
import logging
import sys

from fastmcp import FastMCP

from .config import Config
from .comfy_client import ComfyClient, ComfyClientError
from .workflow_loader import WorkflowLoader, WorkflowInfo
from .workflow_utils import extract_params, inject_params, list_nodes, check_missing_nodes, auto_fix_workflow
from .error_handler import classify_error, apply_fix
from .image_utils import save_outputs

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

# Global state
mcp = FastMCP("operit-comfyui-mcp")
config = Config()
_loaded_workflows: dict[str, WorkflowInfo] = {}


def _get_client() -> ComfyClient:
    return ComfyClient(config)


@mcp.tool()
async def comfy_connect(host: str | None = None) -> str:
    """Get or set the ComfyUI server address.

    Args:
        host: Optional new host address, e.g. "127.0.0.1:8188".
              Leave empty to check current connection.
    """
    global config
    if host:
        config.comfyui_host = host
        return f"ComfyUI host set to: {host}"
    else:
        try:
            client = _get_client()
            stats = await client.get_system_stats()
            await client.close()
            return (
                f"Connected to ComfyUI at {config.comfyui_host}\n"
                f"Python: {stats.get('system', {}).get('python_version', 'unknown')}\n"
                f"Devices: {json.dumps(stats.get('devices', []), indent=2)}"
            )
        except Exception as e:
            return f"Cannot connect to ComfyUI at {config.comfyui_host}: {e}"


@mcp.tool()
async def comfy_system_stats() -> str:
    """Get ComfyUI system information: Python version, CUDA/GPU, VRAM usage."""
    client = _get_client()
    try:
        stats = await client.get_system_stats()
        return json.dumps(stats, indent=2)
    finally:
        await client.close()


@mcp.tool()
async def comfy_list_nodes() -> str:
    """List all available node types installed in ComfyUI."""
    client = _get_client()
    try:
        info = await client.get_object_info()
        node_list = sorted(info.keys())
        lines = [f"**{len(node_list)} node types installed:**", ""]
        for n in node_list:
            lines.append(f"- `{n}`")
        return "\n".join(lines)
    finally:
        await client.close()


@mcp.tool()
async def comfy_list_models(folder: str = "checkpoints") -> str:
    """List available models in a specific folder."""
    client = _get_client()
    try:
        models = await client.get_models(folder)
        if not models:
            return f"No models found in '{folder}'."
        lines = [f"**Models in {folder}:**", ""]
        for m in models:
            lines.append(f"- `{m}`")
        return "\n".join(lines)
    finally:
        await client.close()


@mcp.tool()
async def comfy_list_workflows() -> str:
    """List all available workflows."""
    global _loaded_workflows
    loader = WorkflowLoader()
    builtins = loader.load_builtin_templates()
    lines = ["## Available Workflows", ""]
    if builtins:
        lines.append("### Built-in Templates")
        for wf in builtins:
            nodes = ", ".join(list(set(n.class_type for n in list_nodes(wf.json)))[:5])
            lines.append(f"- **{wf.name}** ({len(wf.nodes)} nodes: {nodes}...)")
            _loaded_workflows[wf.name] = wf
    imported = {k: v for k, v in _loaded_workflows.items() if v.source != "builtin"}
    if imported:
        lines.append("")
        lines.append("### Imported Workflows")
        for name, wf in imported.items():
            lines.append(f"- **{name}** (source: {wf.source}, {len(wf.nodes)} nodes)")
    return "\n".join(lines)


@mcp.tool()
async def comfy_load_workflow(name: str | None = None, json_string: str | None = None, file_path: str | None = None) -> str:
    """Load a workflow for later use."""
    global _loaded_workflows
    if name and not json_string and not file_path:
        if name in _loaded_workflows:
            return f"Workflow **{name}** is loaded."
        else:
            return f"Workflow '{name}' not found."
    if file_path:
        loader = WorkflowLoader()
        wf_info = loader.load_from_file(file_path)
        _loaded_workflows[wf_info.name] = wf_info
        return f"Workflow **{wf_info.name}** loaded from file."
    if json_string:
        wf_info = WorkflowLoader.load_from_string(name or "inline_workflow", json_string)
        _loaded_workflows[wf_info.name] = wf_info
        return f"Workflow **{wf_info.name}** loaded."
    return "Please provide name, json_string, or file_path."


@mcp.tool()
async def comfy_get_workflow_params(name: str) -> str:
    """Extract all tunable parameters from a loaded workflow."""
    if name not in _loaded_workflows:
        return f"Workflow '{name}' not loaded."
    wf_info = _loaded_workflows[name]
    params = extract_params(wf_info.json)
    if not params:
        return f"No tunable parameters found in '{name}'."
    lines = [f"## Parameters for **{name}**", ""]
    for p in params:
        opt_str = f" (options: {', '.join(p.options[:10])})" if p.options else ""
        lines.append(f"- **{p.param_name}** ({p.param_type}) = `{p.current_value}` [node {p.node_id}: {p.title}]{opt_str}")
    return "\n".join(lines)


@mcp.tool()
async def comfy_get_recent_workflows(limit: int = 10) -> str:
    """List recently executed workflows from ComfyUI history."""
    limit = min(limit, 50)
    client = _get_client()
    try:
        all_history = await client.get_history()
    except Exception as e:
        await client.close()
        return f"Failed to fetch history: {e}"
    await client.close()
    if not all_history:
        return "No history found."
    entries = list(all_history.items())[-limit:]
    lines = [f"## Recent Workflows ({min(limit, len(entries))})", ""]
    for pid, entry in reversed(entries):
        status = entry.get("status", {})
        completed = status.get("completed", True)
        status_icon = "✅" if completed else "❌"
        wf_json = {}
        if isinstance(entry.get("prompt"), list) and len(entry["prompt"]) > 2:
            wf_json = entry["prompt"][2] if isinstance(entry["prompt"][2], dict) else {}
        model_name = "unknown"
        for node_id, node in wf_json.items():
            if node.get("class_type") in ("CheckpointLoaderSimple", "UNETLoader"):
                if node.get("class_type") == "CheckpointLoaderSimple":
                    model_name = node.get("inputs", {}).get("ckpt_name", "unknown")
                else:
                    model_name = node.get("inputs", {}).get("unet_name", "unknown")
                break
        pos_prompt = ""
        for node in wf_json.values():
            if node.get("class_type") == "CLIPTextEncode":
                text = node.get("inputs", {}).get("text", "")
                if not pos_prompt:
                    pos_prompt = text[:80]
        outputs = entry.get("outputs", {})
        output_count = sum(len(v.get("images", [])) + len(v.get("gifs", [])) for v in outputs.values())
        lines.append(f"{status_icon} **`{pid[:8]}…`** | {model_name[:40]} | → {output_count} output(s)")
        if pos_prompt:
            lines.append(f"   📝 `{pos_prompt}…`")
    return "\n".join(lines)


@mcp.tool()
async def comfy_load_from_history(prompt_id: str, name: str | None = None) -> str:
    """Load a workflow from ComfyUI history by its prompt_id."""
    global _loaded_workflows
    client = _get_client()
    try:
        history = await client.get_history(prompt_id)
    except Exception as e:
        await client.close()
        return f"Failed to fetch history: {e}"
    await client.close()
    if prompt_id not in history:
        return f"Prompt `{prompt_id}` not found."
    entry = history[prompt_id]
    prompt_data = entry.get("prompt", [])
    wf_json = {}
    if isinstance(prompt_data, list) and len(prompt_data) > 2:
        wf_json = prompt_data[2] if isinstance(prompt_data[2], dict) else {}
    if not wf_json:
        return "Could not extract workflow JSON."
    wf_name = name or f"history_{prompt_id[:8]}"
    wf_info = WorkflowInfo(name=wf_name, source="history", nodes=list(wf_json.keys()), json=wf_json)
    _loaded_workflows[wf_name] = wf_info
    return f"✅ Loaded **{wf_name}** from history"


@mcp.tool()
async def comfy_generate(workflow_name: str, params: dict | str | None = None, wait: bool = True) -> str:
    """Execute a loaded workflow with optional parameter overrides."""
    if workflow_name not in _loaded_workflows:
        return f"Workflow '{workflow_name}' not loaded."
    wf_info = _loaded_workflows[workflow_name]
    workflow = wf_info.json
    if params:
        param_dict = params if isinstance(params, dict) else json.loads(params)
        workflow = inject_params(workflow, param_dict)
    client = _get_client()
    try:
        result = await client.submit_prompt(workflow)
    except Exception as e:
        await client.close()
        return f"Submission failed: {e}"
    if "error" in result or "node_errors" in result:
        await client.close()
        return f"Workflow validation failed."
    prompt_id = result.get("prompt_id", "unknown")
    if not wait:
        await client.close()
        return f"Submitted! prompt_id: `{prompt_id}`."
    for attempt in range(config.max_poll_attempts):
        await asyncio.sleep(config.poll_interval)
        try:
            history = await client.get_history(prompt_id)
        except Exception:
            continue
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("completed") is False:
                await client.close()
                return f"Execution failed: {status.get('status_str', 'error')}"
            try:
                outputs = await save_outputs(client, entry, config.download_dir)
            except Exception as e:
                await client.close()
                return f"Completed but failed to save: {e}"
            await client.close()
            if not outputs:
                return f"Done but no outputs. prompt_id: `{prompt_id}`"
            lines = [f"**Generation complete!**", f"Outputs ({len(outputs)}):"]
            for o in outputs:
                lines.append(f"  - `file://{o.filepath}` ({o.media_type})")
            return "\n".join(lines)
    await client.close()
    return f"Timed out waiting for `{prompt_id}`."


@mcp.tool()
async def comfy_get_result(prompt_id: str) -> str:
    """Check the status and retrieve results of a previously submitted prompt."""
    client = _get_client()
    try:
        history = await client.get_history(prompt_id)
    except Exception as e:
        await client.close()
        return f"Failed: {e}"
    await client.close()
    if prompt_id not in history:
        return f"Prompt `{prompt_id}` not found."
    entry = history[prompt_id]
    outputs = entry.get("outputs", {})
    if not outputs:
        return f"Status: {entry.get('status', {}).get('status_str', 'pending')}"
    client = _get_client()
    try:
        saved = await save_outputs(client, entry, config.download_dir)
    except Exception as e:
        await client.close()
        return f"Download failed: {e}"
    await client.close()
    lines = [f"**Results for {prompt_id}**", f"Outputs ({len(saved)}):"]
    for o in saved:
        lines.append(f"  - `file://{o.filepath}` ({o.media_type})")
    return "\n".join(lines)


@mcp.tool()
async def comfy_queue_status() -> str:
    """Get the current execution queue status."""
    client = _get_client()
    try:
        queue = await client.get_queue()
        running = queue.get("queue_running", [])
        pending = queue.get("queue_pending", [])
        await client.close()
        return f"**Queue Status**\nRunning: {len(running)}\nPending: {len(pending)}"
    except Exception as e:
        await client.close()
        return f"Failed: {e}"


@mcp.tool()
async def comfy_interrupt() -> str:
    """Cancel the currently executing workflow."""
    client = _get_client()
    try:
        await client.interrupt()
        await client.close()
        return "Execution interrupted."
    except Exception as e:
        await client.close()
        return f"Failed: {e}"


@mcp.tool()
async def comfy_free_vram(unload_models: bool = True, free_memory: bool = True) -> str:
    """Free VRAM by unloading models and/or freeing cached memory."""
    client = _get_client()
    try:
        await client.free_vram(unload_models, free_memory)
        await client.close()
        return "VRAM freed."
    except Exception as e:
        await client.close()
        return f"Failed: {e}"


@mcp.tool()
async def comfy_upload_image(file_path: str) -> str:
    """Upload a local image to ComfyUI's input directory."""
    if not os.path.isfile(file_path):
        return f"File not found: {file_path}"
    client = _get_client()
    try:
        result = await client.upload_image(file_path)
        await client.close()
        return f"Image uploaded: `{result.get('name', os.path.basename(file_path))}`"
    except Exception as e:
        await client.close()
        return f"Upload failed: {e}"


@mcp.tool()
async def comfy_check_compatibility(name: str) -> str:
    """Check if a loaded workflow has nodes missing from your ComfyUI install."""
    if name not in _loaded_workflows:
        return f"Workflow '{name}' not loaded."
    wf_info = _loaded_workflows[name]
    client = _get_client()
    try:
        obj_info = await client.get_object_info()
    except Exception as e:
        await client.close()
        return f"Failed: {e}"
    await client.close()
    report = check_missing_nodes(wf_info.json, obj_info)
    if report.warning == "All nodes available.":
        return f"✅ All nodes in **{name}** are installed!"
    lines = [f"## Compatibility Check: **{name}**", ""]
    if report.missing:
        lines.append(f"### Missing ({len(report.missing)})")
        for m in report.missing:
            status = "🔄" if m in report.replaced else "❌"
            lines.append(f"  {status} `{m}`")
    if report.replaced:
        lines.append("")
        lines.append("### Auto-Mapped Replacements")
        for old, new in report.replaced.items():
            lines.append(f"  `{old}` → `{new}`")
    if report.unfixable:
        lines.append("")
        lines.append(f"### ❌ Unfixable ({len(report.unfixable)})")
        for u in report.unfixable:
            lines.append(f"  - `{u}`")
    return "\n".join(lines)


@mcp.tool()
async def comfy_fix_workflow(name: str) -> str:
    """Auto-replace missing nodes with locally installed equivalents."""
    global _loaded_workflows
    if name not in _loaded_workflows:
        return f"Workflow '{name}' not loaded."
    wf_info = _loaded_workflows[name]
    client = _get_client()
    try:
        obj_info = await client.get_object_info()
    except Exception as e:
        await client.close()
        return f"Failed: {e}"
    await client.close()
    new_wf, report = auto_fix_workflow(wf_info.json, obj_info)
    if not report.replaced:
        if report.unfixable:
            return f"⚠️ Could not fix: {', '.join(report.unfixable)}"
        return f"✅ **{name}** has all nodes."
    _loaded_workflows[name] = WorkflowInfo(name=name, source=wf_info.source, nodes=list(new_wf.keys()), json=new_wf)
    lines = [f"## 🔧 Fixed: **{name}**", ""]
    for old, new in report.replaced.items():
        lines.append(f"  `{old}` → `{new}`")
    if report.unfixable:
        lines.append(f"### ⚠️ Unfixable: {', '.join(report.unfixable)}")
    return "\n".join(lines)


@mcp.tool()
async def comfy_quick_gen(file_path: str, params: dict | str | None = None, name: str | None = None) -> str:
    """Load a workflow from file, inject params, and generate in one call."""
    global _loaded_workflows
    loader = WorkflowLoader()
    try:
        wf_info = loader.load_from_file(file_path)
    except Exception as e:
        return f"Failed to load workflow: {e}"
    if name:
        wf_info.name = name
    try:
        param_dict = params if isinstance(params, dict) else json.loads(params)
    except json.JSONDecodeError as e:
        return f"Invalid params: {e}"
    workflow = inject_params(wf_info.json, param_dict)
    wf_info.json = workflow
    _loaded_workflows[wf_info.name] = wf_info
    client = _get_client()
    try:
        result = await client.submit_prompt(workflow)
    except Exception as e:
        await client.close()
        return f"Submission failed: {e}"
    prompt_id = result.get("prompt_id", "unknown")
    for attempt in range(config.max_poll_attempts):
        await asyncio.sleep(config.poll_interval)
        try:
            history = await client.get_history(prompt_id)
        except Exception:
            continue
        if prompt_id in history:
            entry = history[prompt_id]
            if entry.get("status", {}).get("completed") is False:
                await client.close()
                return f"Failed: {entry['status'].get('status_str', 'error')}"
            try:
                outputs = await save_outputs(client, entry, config.download_dir)
            except Exception as e:
                await client.close()
                return f"Saved but download failed: {e}"
            await client.close()
            if not outputs:
                return f"Done. prompt_id: `{prompt_id}`"
            lines = [f"**✅ Quick Gen Complete!**", f"Workflow: **{wf_info.name}**", f"Outputs ({len(outputs)}):"]
            for o in outputs:
                lines.append(f"  - `file://{o.filepath}` ({o.media_type})")
            return "\n".join(lines)
    await client.close()
    return f"Timed out. prompt_id: `{prompt_id}`"


def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()