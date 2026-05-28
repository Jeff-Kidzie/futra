"""GET /api/alerts, POST /api/alerts/{id}/acknowledge."""
from fastapi import APIRouter, Depends, Query, HTTPException
from ..auth import require_auth
from ..db import get_db
from ..models import Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert])
async def get_alerts(
    acknowledged: bool | None = Query(None, description="Filter by acknowledged status"),
    user_id: int = Depends(require_auth),
):
    """Get alerts ordered by created_at DESC."""
    db = get_db()
    try:
        if acknowledged is not None:
            rows = db.execute(
                "SELECT * FROM alerts WHERE acknowledged = ? ORDER BY created_at DESC",
                (1 if acknowledged else 0,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC"
            ).fetchall()

        return [
            Alert(
                id=row["id"],
                type=row["type"],
                message=row["message"],
                severity=row["severity"],
                acknowledged=bool(row["acknowledged"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
    finally:
        db.close()


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    user_id: int = Depends(require_auth),
):
    """Mark an alert as acknowledged."""
    db = get_db()
    try:
        cursor = db.execute(
            "UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,)
        )
        db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"status": "ok"}
    finally:
        db.close()
