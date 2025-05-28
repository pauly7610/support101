from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text
from datetime import datetime, timedelta
from apps.backend.app.core.db import get_db

router = APIRouter(tags=["Analytics"])

@router.get("/escalations")
async def get_escalation_analytics(
    db: AsyncSession = Depends(get_db)
):
    """Get escalation metrics"""
    # Use raw SQL for demo purposes; in production, use SQLAlchemy models
    result = await db.execute(text('''
        SELECT 
            COUNT(*) AS total_escalations,
            AVG(escalation_time) AS avg_response_time,
            DATE_TRUNC('day', created_at) AS date
        FROM escalations
        WHERE TRUE
        GROUP BY date
        ORDER BY date
    '''))
    rows = result.fetchall()
    return {
        "escalations": [dict(row) for row in rows],
        "timeframe": f"{(datetime.now() - timedelta(days=30)).date()} to {datetime.now().date()}"
    }
