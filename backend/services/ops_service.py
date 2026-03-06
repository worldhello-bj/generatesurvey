import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date

from models.ops import OpsRecord
from config import settings

logger = logging.getLogger(__name__)


async def record(
    db: AsyncSession,
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
    rec = OpsRecord(
        task_type=task_type,
        user_id=user_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        cost=cost,
        success=success,
        metadata_=metadata,
    )
    db.add(rec)
    try:
        await db.flush()
    except Exception as exc:
        logger.error("Failed to write ops record: %s", exc)


async def get_today_stats(db: AsyncSession) -> Dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(
            func.count(OpsRecord.id).label("call_count"),
            func.coalesce(func.sum(OpsRecord.cost), 0).label("total_cost"),
            func.coalesce(func.sum(OpsRecord.total_tokens), 0).label("total_tokens"),
            func.count(func.distinct(OpsRecord.user_id)).label("unique_users"),
        ).where(cast(OpsRecord.timestamp, Date) == today)
    )
    row = result.one()
    return {
        "call_count": row.call_count,
        "total_cost": float(row.total_cost),
        "total_tokens": int(row.total_tokens),
        "unique_users": row.unique_users,
    }


async def get_cost_trend(db: AsyncSession, days: int = 7) -> list:
    from sqlalchemy import text
    sql = text(
        """
        SELECT DATE(timestamp) as day,
               COALESCE(SUM(cost), 0) as daily_cost,
               COUNT(*) as call_count
        FROM ops_records
        WHERE timestamp >= (NOW() - INTERVAL '1 day' * :days)
        GROUP BY day
        ORDER BY day
        """
    )
    result = await db.execute(sql, {"days": days})
    return [
        {"date": str(row.day), "cost": float(row.daily_cost), "calls": int(row.call_count)}
        for row in result
    ]


async def get_records(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    task_type: Optional[str] = None,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    query = select(OpsRecord)
    count_query = select(func.count(OpsRecord.id))

    if task_type:
        query = query.where(OpsRecord.task_type == task_type)
        count_query = count_query.where(OpsRecord.task_type == task_type)
    if user_id:
        query = query.where(OpsRecord.user_id == user_id)
        count_query = count_query.where(OpsRecord.user_id == user_id)
    if model:
        query = query.where(OpsRecord.model == model)
        count_query = count_query.where(OpsRecord.model == model)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(OpsRecord.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "task_type": r.task_type,
                "user_id": r.user_id,
                "model": r.model,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "cost": r.cost,
                "success": r.success,
            }
            for r in records
        ],
    }
