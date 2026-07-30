"""Async HTTP client for ComfyUI REST API."""

import httpx
from .config import Config


class ComfyClientError(Exception):
    """Base error for ComfyUI API calls."""
    pass


class ComfyClient:
    """Async HTTP client wrapping ComfyUI's REST API."""

    def __init__(self, config: Config):
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.request_timeout,
        )

    async def close(self):
        await self._client.aclose()

    async def _get(self, path: str) -> dict:
        """GET request, returns parsed JSON dict."""
        resp = await self._client.get(path)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, data: dict) -> dict:
        """POST request with JSON body, returns parsed JSON dict."""
        resp = await self._client.post(path, json=data)
        if resp.status_code >= 400:
            try:
                return resp.json()
            except Exception:
                resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {}

    # System
    async def get_object_info(self) -> dict:
        return await self._get("/object_info")

    async def get_object_info_node(self, node_class: str) -> dict:
        return await self._get(f"/object_info/{node_class}")

    async def get_system_stats(self) -> dict:
        return await self._get("/system_stats")

    async def get_models(self, folder: str = "checkpoints") -> list:
        return await self._get(f"/models/{folder}")

    async def get_embeddings(self) -> list:
        return await self._get("/embeddings")

    async def get_extensions(self) -> list:
        return await self._get("/extensions")

    async def free_vram(self, unload_models: bool = True, free_memory: bool = True) -> dict:
        return await self._post("/free", {"unload_models": unload_models, "free_memory": free_memory})

    # Execution
    async def submit_prompt(self, workflow: dict, client_id: str = "", front: bool = False, extra_data: dict | None = None) -> dict:
        payload = {"prompt": workflow, "client_id": client_id, "front": front}
        if extra_data:
            payload["extra_data"] = extra_data
        return await self._post("/prompt", payload)

    async def get_prompt_queue(self) -> dict:
        return await self._get("/prompt")

    async def get_queue(self) -> dict:
        return await self._get("/queue")

    async def delete_queue_item(self, item_id: str) -> dict:
        return await self._post("/queue", {"delete": [item_id]})

    async def clear_queue(self) -> dict:
        return await self._post("/queue", {"clear": True})

    async def interrupt(self) -> dict:
        return await self._post("/interrupt", {})

    async def get_history(self, prompt_id: str | None = None) -> dict:
        path = f"/history/{prompt_id}" if prompt_id else "/history"
        return await self._get(path)

    async def clear_history(self) -> dict:
        return await self._post("/history", {"clear": True})

    # Files
    async def upload_image(self, file_path: str, overwrite: bool = True) -> dict:
        import os
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        resp = await self._client.post(
            "/upload/image",
            files={"image": (filename, content)},
            params={"overwrite": str(overwrite).lower()},
        )
        resp.raise_for_status()
        return resp.json()

    async def upload_mask(self, file_path: str, original_ref: str = "", overwrite: bool = True) -> dict:
        import os
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        params = {"overwrite": str(overwrite).lower()}
        if original_ref:
            params["original_ref"] = original_ref
        resp = await self._client.post("/upload/mask", files={"image": (filename, content)}, params=params)
        resp.raise_for_status()
        return resp.json()

    async def download_output(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        resp = await self._client.get("/view", params=params)
        resp.raise_for_status()
        return resp.content