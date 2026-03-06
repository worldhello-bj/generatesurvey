import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)
_OPS_FILE = Path(__file__).resolve().parents[1] / "data" / "ops_records.json"
_OPS_LOCK = asyncio.Lock()
_MIN_TS = datetime.min.replace(tzinfo=timezone.utc)


def _ensure_file() -> None:
    _OPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _OPS_FILE.exists():
        _OPS_FILE.write_text("[]", encoding="utf-8")


def _load_records() -> list[Dict[str, Any]]:
    _ensure_file()
    try:
        data = json.loads(_OPS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        logger.warning("Failed to load ops records file %s, reset to empty list.", _OPS_FILE, exc_info=True)
        return []


def _save_records(records: list[Dict[str, Any]]) -> None:
    _ensure_file()
    tmp_file = _OPS_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_file.replace(_OPS_FILE)


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def record(
    task_type: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    success: bool = True,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    total = prompt_tokens + completion_tokens
    cost = (
        prompt_tokens / 1000 * settings.prompt_token_price
        + completion_tokens / 1000 * settings.completion_token_price
    )
    async with _OPS_LOCK:
        records = _load_records()
        next_id = max((_as_int(r.get("id", 0), default=0) for r in records), default=0) + 1
        records.append(
            {
                "id": next_id,
                "task_type": task_type,
                "user_id": user_id,
                "model": model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total,
                "cost": cost,
                "success": success,
                "metadata": metadata or {},
            }
        )
        _save_records(records)


async def get_today_stats() -> Dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    async with _OPS_LOCK:
        records = _load_records()

    today_records = []
    for rec in records:
        ts = _parse_ts(rec.get("timestamp"))
        if ts and ts.date() == today:
            today_records.append(rec)

    return {
        "call_count": len(today_records),
        "total_cost": float(sum(_as_float(r.get("cost", 0), default=0.0) for r in today_records)),
        "total_tokens": int(sum(_as_int(r.get("total_tokens", 0), default=0) for r in today_records)),
        "unique_users": len({r.get("user_id") for r in today_records if r.get("user_id")}),
    }


async def get_cost_trend(days: int = 7) -> list:
    async with _OPS_LOCK:
        records = _load_records()

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    trend = {
        (start_date + timedelta(days=i)): {"cost": 0.0, "calls": 0}
        for i in range((end_date - start_date).days + 1)
    }

    for rec in records:
        ts = _parse_ts(rec.get("timestamp"))
        if not ts:
            continue
        day = ts.date()
        if day in trend:
            trend[day]["cost"] += _as_float(rec.get("cost", 0), default=0.0)
            trend[day]["calls"] += 1

    return [
        {"date": day.isoformat(), "cost": values["cost"], "calls": values["calls"]}
        for day, values in sorted(trend.items(), key=lambda x: x[0])
    ]


async def get_records(
    page: int = 1,
    page_size: int = 20,
    task_type: Optional[str] = None,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    async with _OPS_LOCK:
        records = _load_records()

    filtered = []
    for rec in records:
        if task_type and rec.get("task_type") != task_type:
            continue
        if user_id and rec.get("user_id") != user_id:
            continue
        if model and rec.get("model") != model:
            continue
        filtered.append(rec)

    filtered.sort(key=lambda r: _parse_ts(r.get("timestamp")) or _MIN_TS, reverse=True)
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = filtered[start:end]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.get("id"),
                "task_type": r.get("task_type"),
                "user_id": r.get("user_id"),
                "model": r.get("model"),
                "timestamp": r.get("timestamp"),
                "prompt_tokens": _as_int(r.get("prompt_tokens", 0), default=0),
                "completion_tokens": _as_int(r.get("completion_tokens", 0), default=0),
                "total_tokens": _as_int(r.get("total_tokens", 0), default=0),
                "cost": _as_float(r.get("cost", 0), default=0.0),
                "success": bool(r.get("success", False)),
            }
            for r in page_items
        ],
    }
