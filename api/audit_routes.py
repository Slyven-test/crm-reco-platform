"""API routes for audit and quality management."""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from core.audit.service import AuditService, QualityService, GatingService
from core.audit.models import ApprovalStatus
from api.dependencies import get_db

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


# ============================================================================
# AUDIT ENDPOINTS
# ============================================================================

@router.get("/logs")
def get_audit_logs(
    db: Session = None,
    customer_code: Optional[str] = None,
    run_id: Optional[str] = None,
    approval_status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
) -> Dict:
    """Get audit logs with optional filtering.

    Query Parameters:
    - customer_code: Filter by customer (optional)
    - run_id: Filter by run (optional)
    - approval_status: Filter by status (PENDING, APPROVED, REJECTED, FLAGGED)
    - limit: Max results (1-1000, default 100)
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    audit_service = AuditService(db)

    if customer_code:
        logs = audit_service.get_audit_history(customer_code, limit)
    else:
        # Get generic logs (implement in service if needed)
        logs = []

    return {
        "total": len(logs),
        "logs": logs,
        "query": {
            "customer_code": customer_code,
            "run_id": run_id,
            "approval_status": approval_status,
        },
    }


@router.get("/logs/{audit_id}")
def get_audit_log(
    audit_id: str,
    db: Session = None,
) -> Dict:
    """Get specific audit log entry."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    from core.database import AuditLogDB

    log = db.query(AuditLogDB).filter(AuditLogDB.audit_id == audit_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return log.to_dict()


@router.get("/pending")
def get_pending_approvals(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = None,
) -> Dict:
    """Get pending recommendations awaiting approval."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    audit_service = AuditService(db)
    pending = audit_service.get_pending_approvals(limit)

    return {
        "total": len(pending),
        "pending": pending,
    }


@router.get("/flagged")
def get_flagged_recommendations(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = None,
) -> Dict:
    """Get flagged recommendations for review."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    audit_service = AuditService(db)
    flagged = audit_service.get_flagged_recommendations(limit)

    return {
        "total": len(flagged),
        "flagged": flagged,
    }


# ============================================================================
# APPROVAL ENDPOINTS
# ============================================================================

@router.post("/approve/{audit_id}")
def approve_recommendation(
    audit_id: str,
    approved_by: str = Query(...),
    reason: Optional[str] = None,
    db: Session = None,
) -> Dict:
    """Approve a recommendation."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    audit_service = AuditService(db)
    success = audit_service.approve_recommendation(
        audit_id=audit_id,
        approved_by=approved_by,
        reason=reason,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return {
        "audit_id": audit_id,
        "status": "APPROVED",
        "approved_by": approved_by,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/reject/{audit_id}")
def reject_recommendation(
    audit_id: str,
    approved_by: str = Query(...),
    reason: str = Query(...),
    db: Session = None,
) -> Dict:
    """Reject a recommendation."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    audit_service = AuditService(db)
    success = audit_service.reject_recommendation(
        audit_id=audit_id,
        approved_by=approved_by,
        reason=reason,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return {
        "audit_id": audit_id,
        "status": "REJECTED",
        "approved_by": approved_by,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/flag/{audit_id}")
def flag_recommendation(
    audit_id: str,
    reason: str = Query(...),
    db: Session = None,
) -> Dict:
    """Flag a recommendation for review."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    audit_service = AuditService(db)
    success = audit_service.flag_recommendation(
        audit_id=audit_id,
        flag_reason=reason,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return {
        "audit_id": audit_id,
        "status": "FLAGGED",
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# QUALITY METRICS ENDPOINTS
# ============================================================================

@router.get("/quality/metrics/{run_id}")
def get_quality_metrics(
    run_id: str,
    total_customers: int = Query(1000),
    db: Session = None,
) -> Dict:
    """Get quality metrics for a run."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    quality_service = QualityService(db)
    metrics = quality_service.compute_quality_metrics(run_id, total_customers)

    return metrics.to_dict()


@router.get("/quality/report")
def get_quality_report(
    days: int = Query(7, ge=1, le=90),
    db: Session = None,
) -> Dict:
    """Get quality report for recent runs."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    quality_service = QualityService(db)
    report = quality_service.get_quality_report(days)

    return report


# ============================================================================
# GATING ENDPOINTS
# ============================================================================

@router.post("/gating/check/{recommendation_id}")
def check_recommendation_gating(
    recommendation_id: str,
    policy: str = Query("standard"),
    db: Session = None,
) -> Dict:
    """Check if recommendation passes gating policy."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    from core.database import RecommendationItem

    reco = db.query(RecommendationItem).filter(
        RecommendationItem.recommendation_key == recommendation_id
    ).first()

    if not reco:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    gating_service = GatingService(db)
    passed, issues = gating_service.check_recommendation(reco, policy)

    return {
        "recommendation_id": recommendation_id,
        "policy": policy,
        "passed": passed,
        "issues": issues,
    }


@router.post("/gating/check-batch")
def check_batch_gating(
    run_id: str = Query(...),
    policy: str = Query("standard"),
    db: Session = None,
) -> Dict:
    """Check batch of recommendations against gating policy."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    from core.database import RecommendationItem

    recos = db.query(RecommendationItem).filter(
        RecommendationItem.run_id == run_id
    ).all()

    if not recos:
        raise HTTPException(status_code=404, detail="No recommendations found for run")

    gating_service = GatingService(db)
    result = gating_service.check_batch(recos, policy)

    return {
        "run_id": run_id,
        "policy": policy,
        **result,
    }


# ============================================================================
# COMPLIANCE ENDPOINTS
# ============================================================================

@router.get("/compliance/summary")
def get_compliance_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = None,
) -> Dict:
    """Get compliance summary."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    from core.database import AuditLogDB
    from sqlalchemy import func

    # Count by status
    status_counts = db.query(
        AuditLogDB.approval_status,
        func.count(AuditLogDB.audit_id).label('count')
    ).group_by(AuditLogDB.approval_status).all()

    status_summary = {status: count for status, count in status_counts}

    # Total
    total = sum(status_summary.values())

    # Approval rate
    approved = status_summary.get('APPROVED', 0)
    approval_rate = (approved / total * 100) if total > 0 else 0

    return {
        "total_recommendations": total,
        "approval_summary": status_summary,
        "approval_rate": round(approval_rate, 2),
    }
