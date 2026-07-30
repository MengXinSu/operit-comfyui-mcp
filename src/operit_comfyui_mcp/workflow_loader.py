"""Discover and load workflows from built-in templates and remote ComfyUI."""

import json
import os
import glob
import logging
from dataclasses import dataclass, field

from .workflow_utils import _normalize_workflow

logger = logging.getLogger(__name__)


@dataclass
class WorkflowInfo:
    name: str
    source: str
    file_path: str | None = None
    nodes: list[str] = field(default_factory=list)
    json: dict = field(default_factory=dict)


class WorkflowLoader:
    def __init__(self, builtin_dir: str | None = None):
        if builtin_dir is None:
            builtin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workflows")
        self.builtin_dir = builtin_dir

    def load_builtin_templates(self) -> list[WorkflowInfo]:
        workflows = []
        if not os.path.isdir(self.builtin_dir):
            return workflows
        for file_path in glob.glob(os.path.join(self.builtin_dir, "*.json")):
            try:
                wf = self._load_json_file(file_path)
                name = os.path.splitext(os.path.basename(file_path))[0]
                workflows.append(WorkflowInfo(name=name, source="builtin", file_path=file_path, nodes=list(wf.keys()), json=wf))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Skipping {file_path}: {e}")
        return workflows

    @staticmethod
    def load_from_file(file_path: str) -> WorkflowInfo:
        wf = WorkflowLoader._load_json_file(file_path)
        name = os.path.splitext(os.path.basename(file_path))[0]
        return WorkflowInfo(name=name, source="imported", file_path=file_path, nodes=list(wf.keys()), json=wf)

    @staticmethod
    def load_from_string(name: str, json_str: str) -> WorkflowInfo:
        wf = json.loads(json_str)
        wf = _normalize_workflow(wf)
        return WorkflowInfo(name=name, source="inline", nodes=list(wf.keys()), json=wf)

    @staticmethod
    def _load_json_file(file_path: str) -> dict:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"File must contain a JSON object: {file_path}")
        keys = list(data.keys())
        if len(keys) == 1 and isinstance(data[keys[0]], str):
            try:
                inner = json.loads(data[keys[0]])
                if isinstance(inner, dict):
                    data = inner
            except (json.JSONDecodeError, TypeError):
                pass
        data = _normalize_workflow(data)
        for node_id, node in data.items():
            if not isinstance(node_id, str):
                raise ValueError(f"Node IDs must be strings: {file_path}")
            if "class_type" not in node:
                raise ValueError(f"Node {node_id} missing class_type: {file_path}")
        return data