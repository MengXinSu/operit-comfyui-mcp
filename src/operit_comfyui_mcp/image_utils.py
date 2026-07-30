from dataclasses import dataclass
import os


@dataclass
class OutputFile:
    filepath: str
    media_type: str


async def save_outputs(client, entry: dict, download_dir: str) -> list[OutputFile]:
    """Download and save all output images from a completed workflow entry."""
    os.makedirs(download_dir, exist_ok=True)
    outputs = entry.get("outputs", {})
    saved = []

    for node_id, node_output in outputs.items():
        images = node_output.get("images", [])
        for img in images:
            filename = img.get("filename", "")
            subfolder = img.get("subfolder", "")
            img_type = img.get("type", "output")
            try:
                data = await client.download_output(filename, subfolder, img_type)
            except Exception:
                continue
            local_path = os.path.join(download_dir, filename)
            with open(local_path, "wb") as f:
                f.write(data)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
            media_type = f"image/{ext}"
            saved.append(OutputFile(filepath=local_path, media_type=media_type))

        gifs = node_output.get("gifs", [])
        for gif in gifs:
            filename = gif.get("filename", "")
            subfolder = gif.get("subfolder", "")
            try:
                data = await client.download_output(filename, subfolder, "output")
            except Exception:
                continue
            local_path = os.path.join(download_dir, filename)
            with open(local_path, "wb") as f:
                f.write(data)
            saved.append(OutputFile(filepath=local_path, media_type="image/gif"))

    return saved