import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

_STORE_FILE = Path(__file__).resolve().parents[1] / "data" / "runtime_store.json"
_STORE_LOCK = asyncio.Lock()
logger = logging.getLogger(__name__)


def _ensure_file() -> None:
    _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _STORE_FILE.exists():
        _STORE_FILE.write_text("{}", encoding="utf-8")


def _load_store() -> dict[str, Any]:
    _ensure_file()
    try:
        data = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to load runtime store file %s, returning empty object.", _STORE_FILE, exc_info=True)
        return {}
    return data if isinstance(data, dict) else {}


def _save_store(store: dict[str, Any]) -> None:
    _ensure_file()
    tmp_file = _STORE_FILE.with_suffix(".tmp")
    try:
        tmp_file.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
        tmp_file.replace(_STORE_FILE)
    except Exception:
        if tmp_file.exists():
            try:
                os.unlink(tmp_file)
            except OSError:
                logger.warning("Failed to cleanup temp store file %s", tmp_file, exc_info=True)
        raise


def _is_expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        expire_dt = datetime.fromisoformat(expires_at)
    except ValueError:
        return True
    return expire_dt <= datetime.now(timezone.utc)


def _cleanup_expired(store: dict[str, Any]) -> bool:
    expired_keys = []
    for key, payload in store.items():
        if not isinstance(payload, dict) or _is_expired(payload.get("expires_at")):
            expired_keys.append(key)
    for key in expired_keys:
        store.pop(key, None)
    return bool(expired_keys)


async def setex(key: str, ttl_seconds: int, value: Any) -> None:
    # ttl_seconds <= 0 means no expiration.
    async with _STORE_LOCK:
        store = _load_store()
        _cleanup_expired(store)
        expire_at = None
        if ttl_seconds > 0:
            expire_dt = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            expire_at = expire_dt.isoformat()
        store[key] = {"value": value, "expires_at": expire_at}
        _save_store(store)


async def get(key: str) -> Optional[Any]:
    async with _STORE_LOCK:
        store = _load_store()
        changed = _cleanup_expired(store)
        payload = store.get(key)
        if not isinstance(payload, dict):
            if changed:
                _save_store(store)
            return None
        if _is_expired(payload.get("expires_at")):
            store.pop(key, None)
            _save_store(store)
            return None
        if changed:
            _save_store(store)
        return payload.get("value")


async def delete(key: str) -> None:
    async with _STORE_LOCK:
        store = _load_store()
        _cleanup_expired(store)
        if key in store:
            store.pop(key, None)
            _save_store(store)
