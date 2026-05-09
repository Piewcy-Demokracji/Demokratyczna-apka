import io
import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app.core.security import get_current_user

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP", "BMP"}

os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_image_path(image_path: Optional[str]) -> Optional[str]:
    if not image_path:
        return None

    normalized = image_path.replace("\\", "/").strip()

    if ".." in normalized.split("/") or normalized.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image path",
        )
    if not normalized.startswith(f"{UPLOAD_DIR}/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image path must reside in uploads directory",
        )
    if not os.path.isfile(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file not found",
        )
    return normalized


def copy_image_for_session(source_path: Optional[str]) -> Optional[str]:
    if not source_path:
        return None
    if not os.path.isfile(source_path):
        return None

    ext = os.path.splitext(source_path)[1] or ".png"
    new_filename = f"{uuid.uuid4().hex}{ext}"
    new_path = os.path.join(UPLOAD_DIR, new_filename)
    shutil.copyfile(source_path, new_path)
    return new_path.replace("\\", "/")


def _validate_and_open(content: bytes) -> Image.Image:
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)} MB)",
        )
    try:
        verify_img = Image.open(io.BytesIO(content))
        verify_img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        )

    img = Image.open(io.BytesIO(content))
    if img.format not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format: {img.format}",
        )
    return img


@router.post("/image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    content = await file.read()
    img = _validate_and_open(content)

    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(UPLOAD_DIR, filename)

    if img.mode in ("RGBA", "LA"):
        img.save(filepath, "PNG", optimize=True)
    else:
        img.convert("RGB").save(filepath, "PNG", optimize=True)

    return {"image_path": f"{UPLOAD_DIR}/{filename}"}