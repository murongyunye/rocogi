from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .adapters.frame import Frame
from .config import RUNTIME_DIR
from .engine_settings import load_cli_settings


def ensure_engine_dir() -> Path:
    path = RUNTIME_DIR / "engine"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_image(image, name: str = "frame.jpg") -> str:
    import cv2

    path = ensure_engine_dir() / Path(name).name
    if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
        path = path.with_suffix(".jpg")
    params = [int(cv2.IMWRITE_JPEG_QUALITY), 88] if path.suffix.lower() in (".jpg", ".jpeg") else []
    ok = cv2.imwrite(str(path), image, params)
    if not ok:
        raise RuntimeError(f"截图保存失败: {path}")
    return str(path)


def load_frame(params: Dict[str, Any], settings: Dict[str, Any]) -> Frame:
    """Load an image from params['image'] or capture the configured target."""
    image_path = params.get("image")
    if image_path:
        import cv2

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
        return Frame(image=image, meta={"source": "image", "path": str(image_path)})

    from .adapters.mock import MockGameTarget, WindowsGameTarget

    target_settings = settings.get("target", {})
    target = (
        WindowsGameTarget(target_settings)
        if target_settings.get("kind") == "windows"
        else MockGameTarget(target_settings)
    )
    frame = target.capture()
    meta = dict(frame.meta or {})
    meta["source"] = "capture"
    meta.setdefault("width", frame.width)
    meta.setdefault("height", frame.height)
    frame.meta = meta
    return frame


def data_result(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, **data}
