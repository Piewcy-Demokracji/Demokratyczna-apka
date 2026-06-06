import io
import os
import shutil
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from PIL import Image

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import (
    PollOption as PollOptionModel,
    PollTemplateOption,
    PollTemplatePublishedOption,
)

router = APIRouter(prefix="/api/upload", tags=["upload"])

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP", "BMP"}

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _normalize_uploads_path(image_path: str) -> str:
    """Normalize and validate that the path is inside UPLOAD_DIR (no traversal)."""
    normalized = image_path.replace("\\", "/").strip()
    if ".." in normalized.split("/") or normalized.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image path")
    if not normalized.startswith(f"{UPLOAD_DIR}/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image path must reside in uploads directory",
        )
    return normalized


def validate_image_path(image_path: Optional[str]) -> Optional[str]:
    """Validate a client-supplied image path. Returns None for empty input."""
    if not image_path:
        return None
    normalized = _normalize_uploads_path(image_path)
    if not os.path.isfile(normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file not found")
    return normalized


def is_image_path_referenced(db: Session, image_path: Optional[str]) -> bool:
    """Check whether any DB row points to the given image path."""
    if not image_path:
        return False
    if db.query(PollTemplateOption).filter(PollTemplateOption.image_path == image_path).first():
        return True
    if db.query(PollTemplatePublishedOption).filter(PollTemplatePublishedOption.image_path == image_path).first():
        return True
    if db.query(PollOptionModel).filter(PollOptionModel.image_path == image_path).first():
        return True
    return False


def copy_image_for_session(source_path: Optional[str]) -> Optional[str]:
    """Always create a physical copy of the file. Used when source is guaranteed referenced."""
    if not source_path:
        return None
    if not os.path.isfile(source_path):
        return None
    ext = os.path.splitext(source_path)[1] or ".png"
    new_filename = f"{uuid.uuid4().hex}{ext}"
    new_path = os.path.join(UPLOAD_DIR, new_filename)
    shutil.copyfile(source_path, new_path)
    return new_path.replace("\\", "/")


def claim_image_for_session(db: Session, source_path: Optional[str]) -> Optional[str]:
    """
    Reserve an image for a session/poll option:
    - If the path is referenced by any existing record, copy it (snapshot isolation).
    - If it's a fresh upload (not referenced anywhere), take ownership directly,
      avoiding a redundant duplicate.
    """
    if not source_path:
        return None
    if not os.path.isfile(source_path):
        return None
    if is_image_path_referenced(db, source_path):
        return copy_image_for_session(source_path)
    return source_path


def safe_delete_image(image_path: Optional[str]) -> None:
    """Delete an image file from disk if it exists. Silent no-op otherwise."""
    if not image_path:
        return
    try:
        if os.path.isfile(image_path):
            os.remove(image_path)
    except OSError:
        pass


def sweep_orphaned_images(db: Session, max_age_seconds: int = 3600) -> int:
    """
    Delete image files in UPLOAD_DIR that are not referenced by any DB record
    AND are older than max_age_seconds. The age threshold protects fresh uploads
    that aren't saved to a template/session yet (the user may still be filling
    out the form). Called opportunistically on login to clean up orphans left by
    browser crashes, power loss, lost connections, etc.

    Returns the number of files deleted.
    """
    if not os.path.isdir(UPLOAD_DIR):
        return 0

    now = time.time()
    deleted = 0
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.isfile(file_path):
            continue
            age = now - os.path.getmtime(file_path)
        except OSError:
            continue
        if age < max_age_seconds:
            continue
        relative_path = f"{UPLOAD_DIR}/{filename}"
        if is_image_path_referenced(db, relative_path):
            continue
        safe_delete_image(relative_path)
        deleted += 1
    return deleted


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

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
    """
    Upload an image (JPEG/PNG/GIF/WEBP/BMP) to be referenced as image_path
    in template options or session option overrides.

    Returns: {"image_path": "uploads/<uuid>.png"}
    """
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


@router.delete("/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    path: str = Query(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Delete an unreferenced image file from disk. If the path is referenced by any
    template/published/poll option, the call is a silent no-op so we never break
    a live record. Path traversal is blocked.
    """
    normalized = _normalize_uploads_path(path)
    if is_image_path_referenced(db, normalized):
        return
    safe_delete_image(normalized)
