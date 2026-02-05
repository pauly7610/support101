from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.jwt import get_current_user
from apps.backend.app.auth.models import User
from apps.backend.app.core.db import get_db

router = APIRouter(tags=["Compliance"])


class UserIdRequest(BaseModel):
    user_id: str


@router.post("/gdpr_delete")
async def gdpr_delete(
    request: UserIdRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR-compliant data deletion endpoint"""
    # Verify requester permissions
    if not getattr(current_user, "is_admin", False):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Insufficient permissions"}
        )
    # Perform cascading deletion
    from sqlalchemy import text

    try:
        await db.execute(
            text("DELETE FROM users WHERE id = :user_id"), {"user_id": request.user_id}
        )
        await db.commit()
        return {"status": "User data permanently deleted"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Database error: {str(e)}"},
        )


@router.post("/ccpa_optout")
async def ccpa_optout(request: UserIdRequest, db: AsyncSession = Depends(get_db)):
    """CCPA opt-out of data sale endpoint"""
    from sqlalchemy import text

    try:
        await db.execute(
            text("UPDATE users SET data_sale_optout = TRUE WHERE id = :user_id"),
            {"user_id": request.user_id},
        )
        await db.commit()
        return {"status": "Opt-out preference recorded"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Database error: {str(e)}"},
        )
