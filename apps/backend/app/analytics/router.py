from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.jwt import get_current_user
from apps.backend.app.auth.models import User
from apps.backend.app.core.db import get_db

router = APIRouter(tags=["Analytics"])


@router.get("/escalations")
async def get_escalation_analytics(
    user_id: str = Query(None, description="Filter by user UUID"),
    start_time: int = Query(None, description="Filter: Unix timestamp start"),
    end_time: int = Query(None, description="Filter: Unix timestamp end"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get escalation metrics (admin only, with optional filters)"""
    if not getattr(current_user, "is_admin", False):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Insufficient permissions"},
        )
    filters = ["TRUE"]
    params = {}
    if user_id:
        filters.append("ticket_id = :user_id")
        params["user_id"] = user_id
    if start_time:
        filters.append("created_at >= to_timestamp(:start_time)")
        params["start_time"] = start_time
    if end_time:
        filters.append("created_at <= to_timestamp(:end_time)")
        params["end_time"] = end_time
    filter_sql = " AND ".join(filters)
    sql = f"""
        SELECT
            COUNT(*) AS total_escalations,
            AVG(escalation_time) AS avg_response_time,
            DATE_TRUNC('day', created_at) AS date
        FROM escalations
        WHERE {filter_sql}
        GROUP BY date
        ORDER BY date
    """
    result = await db.execute(text(sql), params)
    rows = result.fetchall()
    return {
        "escalations": [dict(row) for row in rows],
        "timeframe": f"{(datetime.now() - timedelta(days=30)).date()} to {datetime.now().date()}",
    }


@router.get("/escalations/by-agent")
async def get_escalations_by_agent(
    agent_id: str = Query(None, description="Filter by agent (user_id)"),
    start_time: int = Query(None, description="Filter: Unix timestamp start"),
    end_time: int = Query(None, description="Filter: Unix timestamp end"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate escalations by agent (admin only)"""
    if not getattr(current_user, "is_admin", False):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Insufficient permissions"},
        )
    filters = ["TRUE"]
    params = {}
    if agent_id:
        filters.append("user_id = :agent_id")
        params["agent_id"] = agent_id
    if start_time:
        filters.append("created_at >= to_timestamp(:start_time)")
        params["start_time"] = start_time
    if end_time:
        filters.append("created_at <= to_timestamp(:end_time)")
        params["end_time"] = end_time
    filter_sql = " AND ".join(filters)
    sql = f"""
        SELECT
            user_id AS agent_id,
            COUNT(*) AS total_escalations,
            AVG(escalation_time) AS avg_response_time
        FROM escalations
        WHERE {filter_sql}
        GROUP BY user_id
        ORDER BY total_escalations DESC
    """
    result = await db.execute(text(sql), params)
    rows = result.fetchall()
    return {
        "by_agent": [dict(row) for row in rows],
        "filters": {
            "agent_id": agent_id,
            "start_time": start_time,
            "end_time": end_time,
        },
    }


@router.get("/escalations/by-category")
async def get_escalations_by_category(
    category: str = Query(None, description="Filter by escalation category"),
    start_time: int = Query(None, description="Filter: Unix timestamp start"),
    end_time: int = Query(None, description="Filter: Unix timestamp end"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate escalations by category (admin only)"""
    if not getattr(current_user, "is_admin", False):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Insufficient permissions"},
        )
    filters = ["TRUE"]
    params = {}
    if category:
        filters.append("category = :category")
        params["category"] = category
    if start_time:
        filters.append("created_at >= to_timestamp(:start_time)")
        params["start_time"] = start_time
    if end_time:
        filters.append("created_at <= to_timestamp(:end_time)")
        params["end_time"] = end_time
    filter_sql = " AND ".join(filters)
    sql = f"""
        SELECT
            category,
            COUNT(*) AS total_escalations,
            AVG(escalation_time) AS avg_response_time
        FROM escalations
        WHERE {filter_sql}
        GROUP BY category
        ORDER BY total_escalations DESC
    """
    result = await db.execute(text(sql), params)
    rows = result.fetchall()
    return {
        "by_category": [dict(row) for row in rows],
        "filters": {
            "category": category,
            "start_time": start_time,
            "end_time": end_time,
        },
    }
