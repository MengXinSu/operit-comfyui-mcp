from dataclasses import dataclass
from typing import Any


@dataclass
class ErrorInfo:
    error_type: str
    message: str
    suggestion: str
    can_retry: bool


def classify_error(result: dict | None, exception: Exception | None) -> ErrorInfo | None:
    if result:
        node_errors = result.get("node_errors", {})
        if node_errors:
            missing_nodes = [k for k, v in node_errors.items() if v.get("errors")]
            if missing_nodes:
                return ErrorInfo(
                    error_type="missing_node",
                    message=f"Missing nodes: {', '.join(missing_nodes)}",
                    suggestion="Install the missing custom nodes or use comfy_check_compatibility",
                    can_retry=False,
                )
        error = result.get("error", {})
        if error:
            err_type = error.get("type", "")
            if "CUDA" in str(error) or "memory" in str(error).lower():
                return ErrorInfo(
                    error_type="out_of_memory",
                    message=str(error),
                    suggestion="Try lowering resolution or use comfy_free_vram",
                    can_retry=True,
                )
            return ErrorInfo(
                error_type=err_type or "unknown",
                message=str(error),
                suggestion="Check workflow parameters and try again",
                can_retry=True,
            )

    if exception:
        err_str = str(exception).lower()
        if "timeout" in err_str or "timed out" in err_str:
            return ErrorInfo(error_type="timeout", message=str(exception), suggestion="Check if ComfyUI is running and reachable", can_retry=True)
        if "connection" in err_str or "refused" in err_str:
            return ErrorInfo(error_type="connection_error", message=str(exception), suggestion="Verify ComfyUI is running at the configured host", can_retry=True)
        if "oom" in err_str or "out of memory" in err_str:
            return ErrorInfo(error_type="out_of_memory", message=str(exception), suggestion="Free VRAM or lower resolution", can_retry=True)

    return None


def apply_fix(error_info: ErrorInfo) -> str | None:
    if error_info.error_type == "out_of_memory":
        return "Will auto-retry with halved resolution"
    if error_info.error_type == "timeout":
        return "Will retry with increased timeout"
    if error_info.can_retry:
        return "Will retry automatically"
    return None