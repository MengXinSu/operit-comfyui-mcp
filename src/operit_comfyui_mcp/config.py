import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration for operit-comfyui-mcp."""

    comfyui_host: str = field(
        default_factory=lambda: os.getenv("COMFYUI_HOST", "127.0.0.1:8188")
    )
    request_timeout: int = 30  # seconds for ComfyUI API calls
    download_dir: str = field(
        default_factory=lambda: os.getenv(
            "COMFYUI_DOWNLOAD_DIR",
            "./comfyui_outputs",
        )
    )
    max_retries: int = 3
    max_poll_attempts: int = 120
    poll_interval: float = 1.0

    @property
    def base_url(self) -> str:
        return f"http://{self.comfyui_host}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.comfyui_host}/ws"
