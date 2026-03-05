import json
import logging
import os

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{token}")
async def download_file(token: str):
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await r.get(f"download:{token}")
        if not raw:
            raise HTTPException(status_code=404, detail="Download link not found or expired")

        info = json.loads(raw)
        file_path = info["file_path"]
        mime = info.get("mime", "application/octet-stream")
        filename = info.get("filename", "download")

        # One-time: delete the token immediately
        await r.delete(f"download:{token}")
    finally:
        await r.aclose()

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
