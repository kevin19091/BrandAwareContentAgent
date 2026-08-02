import os

from backend.vision import UploadError, describe_image, describe_video

MAX_FILES = 5
MAX_TEXT_BYTES = 200 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024

TEXT_EXTS = {".txt"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm"}


def process_uploads(paths: list[str] | None, label: str) -> str:
    """Validate and read a list of uploaded files into one combined text blob.

    label is used only in error messages (e.g. "Brand Guidelines").
    Raises UploadError with a message safe to show directly in the chat.
    """
    if not paths:
        return ""

    if len(paths) > MAX_FILES:
        raise UploadError(f"{label}: up to {MAX_FILES} files allowed, got {len(paths)}.")

    parts = []
    for path in paths:
        name = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()
        size = os.path.getsize(path)

        if ext in TEXT_EXTS:
            if size > MAX_TEXT_BYTES:
                raise UploadError(f"{label}: {name} is too large ({size // 1024} KB, max {MAX_TEXT_BYTES // 1024} KB).")
            with open(path, "r", errors="ignore") as f:
                parts.append(f"[{name}]\n{f.read()}")

        elif ext in IMAGE_EXTS:
            if size > MAX_IMAGE_BYTES:
                raise UploadError(f"{label}: {name} is too large ({size // (1024 * 1024)} MB, max {MAX_IMAGE_BYTES // (1024 * 1024)} MB).")
            parts.append(f"[{name}, image]\n{describe_image(path)}")

        elif ext in VIDEO_EXTS:
            if size > MAX_VIDEO_BYTES:
                raise UploadError(f"{label}: {name} is too large ({size // (1024 * 1024)} MB, max {MAX_VIDEO_BYTES // (1024 * 1024)} MB).")
            parts.append(f"[{name}, video]\n{describe_video(path)}")

        else:
            raise UploadError(f"{label}: {name} has an unsupported file type ({ext}).")

    return "\n\n".join(parts)
