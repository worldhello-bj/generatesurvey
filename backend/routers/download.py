import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.state_store import delete, get

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{token}")
async def download_file(token: str):
    info = await get(f"download:{token}")
    if info is None:
        raise HTTPException(status_code=404, detail="Download link not found or expired")

    file_path = info["file_path"]
    mime = info.get("mime", "application/octet-stream")
    filename = info.get("filename", "download")

    # One-time: delete the token immediately
    await delete(f"download:{token}")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File no longer available")

    return FileResponse(
        path=file_path,
        media_type=mime,
        filename=filename,
        background=_cleanup_file(file_path),
    )


class _cleanup_file:
    """Background task to delete temp file after response is sent."""

    def __init__(self, path: str):
        self.path = path

    async def __call__(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass
