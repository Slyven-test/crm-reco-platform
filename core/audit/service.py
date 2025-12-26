"""Audit and quality management service."""

import uuid
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.audit.models import (
    AuditLog, QualityMetrics, QualityLevel, ApprovalStatus,
    GatingPolicy, ComplianceCheck
)
from core.database import (
    RecommendationItem, Customer, Product, AuditLogDB, QualityMetricsDB
)


class AuditService:
    """Service for audit logging and compliance."""

    def __init__(self, db: Session):
        """Initialize audit service."""
        self.db = db

    def log_recommendation(self, run_id: str, customer_code: str,
                          product_key: str, scenario: str,
                          score: float,
                          approval_status: ApprovalStatus = ApprovalStatus.PENDING) -> AuditLog:
        """Log a recommendation for audit."""
        audit_id = str(uuid.uuid4())

        # Create audit entry
        audit = AuditLog(
            audit_id=audit_id,
            run_id=run_id,
            customer_code=customer_code,
            product_key=product_key,
            scenario=scenario,
            recommendation_score=score,
            approval_status=approval_status,
        )

        # Store in database
        db_entry = AuditLogDB(
            audit_id=audit_id,
            run_id=run_id,
            customer_code=customer_code,
            product_key=product_key,
            scenario=scenario,
            recommendation_score=score,
            approval_status=approval_status.value,
            created_at=datetime.utcnow(),
        )
        self.db.add(db_entry)
        self.db.commit()

        return audit

    def log_batch_recommendations(self, run_id: str,
                                  recommendations: List[Dict]) -> List[AuditLog]:
        """Log multiple recommendations."""
        audit_logs = []
        for reco in recommendations:
            audit = self.log_recommendation(
                run_id=run_id,
                customer_code=reco['customer_code'],
                product_key=reco['product_key'],
                scenario=reco['scenario'],
                score=reco['score'],
            )
            audit_logs.append(audit)
        return audit_logs

    def approve_recommendation(self, audit_id: str, approved_by: str,
                              reason: Optional[str] = None) -> bool:
        """Approve a recommendation."""
        audit_entry = self.db.query(AuditLogDB).filter(
            AuditLogDB.audit_id == audit_id
        ).first()

        if not audit_entry:
            return False

        audit_entry.approval_status = ApprovalStatus.APPROVED.value
        audit_entry.approved_by = approved_by
        audit_entry.approval_reason = reason
        audit_entry.approved_at = datetime.utcnow()
        self.db.commit()

        return True

    def reject_recommendation(self, audit_id: str, approved_by: str,
                             reason: str) -> bool:
        """Reject a recommendation."""
        audit_entry = self.db.query(AuditLogDB).filter(
            AuditLogDB.audit_id == audit_id
        ).first()

        if not audit_entry:
            return False

        audit_entry.approval_status = ApprovalStatus.REJECTED.value
        audit_entry.approved_by = approved_by
        audit_entry.approval_reason = reason
        audit_entry.approved_at = datetime.utcnow()
        self.db.commit()

        return True

    def flag_recommendation(self, audit_id: str, flag_reason: str) -> bool:
        """Flag a recommendation for review."""
        audit_entry = self.db.query(AuditLogDB).filter(
            AuditLogDB.audit_id == audit_id
        ).first()

        if not audit_entry:
            return False

        audit_entry.approval_status = ApprovalStatus.FLAGGED.value
        if not audit_entry.flags:
            audit_entry.flags = []
        audit_entry.flags.append(flag_reason)
        self.db.commit()

        return True

    def get_pending_approvals(self, limit: int = 100) -> List[Dict]:
        """Get pending recommendations for approval."""
        entries = self.db.query(AuditLogDB).filter(
            AuditLogDB.approval_status == ApprovalStatus.PENDING.value
        ).order_by(AuditLogDB.created_at.desc()).limit(limit).all()

        return [{
            'audit_id': e.audit_id,
            'run_id': e.run_id,
            'customer_code': e.customer_code,
            'product_key': e.product_key,
            'scenario': e.scenario,
            'score': e.recommendation_score,
            'created_at': e.created_at.isoformat(),
        } for e in entries]

    def get_flagged_recommendations(self, limit: int = 100) -> List[Dict]:
        """Get flagged recommendations."""
        entries = self.db.query(AuditLogDB).filter(
            AuditLogDB.approval_status == ApprovalStatus.FLAGGED.value
        ).order_by(AuditLogDB.created_at.desc()).limit(limit).all()

        return [{
            'audit_id': e.audit_id,
            'run_id': e.run_id,
            'customer_code': e.customer_code,
            'product_key': e.product_key,
            'scenario': e.scenario,
            'score': e.recommendation_score,
            'flags': e.flags or [],
            'created_at': e.created_at.isoformat(),
        } for e in entries]

    def get_audit_history(self, customer_code: str, limit: int = 50) -> List[Dict]:
        """Get audit history for customer."""
        entries = self.db.query(AuditLogDB).filter(
            AuditLogDB.customer_code == customer_code
        ).order_by(AuditLogDB.created_at.desc()).limit(limit).all()

        return [e.to_dict() for e in entries]


class QualityService:
    """Service for quality metrics and analysis."""

    def __init__(self, db: Session):
        """Initialize quality service."""
        self.db = db

    def compute_quality_metrics(self, run_id: str,
                               total_customers: int) -> QualityMetrics:
        """Compute quality metrics for a run."""
        # Get recommendations for this run
        recos = self.db.query(RecommendationItem).filter(
            RecommendationItem.run_id == run_id
        ).all()

        if not recos:
            return self._empty_metrics(run_id)

        # Coverage score
        unique_customers = len(set(r.customer_code for r in recos))
        coverage_score = unique_customers / max(total_customers, 1)

        # Diversity score
        diversity_score = self._compute_diversity_score(recos)

        # Accuracy score (based on score distribution)
        accuracy_score = self._compute_accuracy_score(recos)

        # Score statistics
        scores = [r.recommendation_score for r in recos]
        avg_score = sum(scores) / len(scores) if scores else 0
        median_score = sorted(scores)[len(scores) // 2] if scores else 0

        # Diversity ratio
        diversity_ratio = self._compute_diversity_ratio(recos)

        # Determine quality level
        quality_score = (
            coverage_score * 0.4 +
            diversity_score * 0.3 +
            accuracy_score * 0.3
        )

        if quality_score >= 0.90:
            quality_level = QualityLevel.EXCELLENT
        elif quality_score >= 0.75:
            quality_level = QualityLevel.GOOD
        elif quality_score >= 0.60:
            quality_level = QualityLevel.ACCEPTABLE
        else:
            quality_level = QualityLevel.POOR

        metrics = QualityMetrics(
            run_id=run_id,
            total_recommendations=len(recos),
            coverage_score=coverage_score,
            diversity_score=diversity_score,
            accuracy_score=accuracy_score,
            avg_score=avg_score,
            median_score=median_score,
            diversity_ratio=diversity_ratio,
            quality_level=quality_level,
        )

        # Store in database
        db_metrics = QualityMetricsDB(
            run_id=run_id,
            total_recommendations=len(recos),
            coverage_score=coverage_score,
            diversity_score=diversity_score,
            accuracy_score=accuracy_score,
            avg_score=avg_score,
            median_score=median_score,
            quality_level=quality_level.value,
            timestamp=datetime.utcnow(),
        )
        self.db.add(db_metrics)
        self.db.commit()

        return metrics

    def _compute_diversity_score(self, recos: List[RecommendationItem]) -> float:
        """Compute product diversity score (0-1)."""
        if not recos:
            return 0.0

        # Get unique products vs total
        unique_products = len(set(r.product_key for r in recos))
        total_recos = len(recos)

        # Score: higher diversity is better (max 1.0 at 70% unique)
        diversity_ratio = unique_products / max(total_recos, 1)
        return min(diversity_ratio / 0.7, 1.0)

    def _compute_accuracy_score(self, recos: List[RecommendationItem]) -> float:
        """Compute estimated accuracy based on score distribution."""
        if not recos:
            return 0.0

        # Higher average scores = higher accuracy estimate
        scores = [r.recommendation_score for r in recos]
        avg_score = sum(scores) / len(scores)
        # Normalize to 0-1 (assuming max score is 100)
        return min(avg_score / 100.0, 1.0)

    def _compute_diversity_ratio(self, recos: List[RecommendationItem]) -> float:
        """Compute average products per customer."""
        if not recos:
            return 0.0

        customer_recos = {}
        for r in recos:
            if r.customer_code not in customer_recos:
                customer_recos[r.customer_code] = []
            customer_recos[r.customer_code].append(r)

        # Count unique products per customer
        ratios = []
        for customer_recos_list in customer_recos.values():
            unique = len(set(r.product_key for r in customer_recos_list))
            total = len(customer_recos_list)
            ratios.append(unique / total if total > 0 else 0)

        return sum(ratios) / len(ratios) if ratios else 0.0

    def _empty_metrics(self, run_id: str) -> QualityMetrics:
        """Return empty metrics."""
        return QualityMetrics(
            run_id=run_id,
            total_recommendations=0,
            coverage_score=0.0,
            diversity_score=0.0,
            accuracy_score=0.0,
            avg_score=0.0,
            median_score=0.0,
            diversity_ratio=0.0,
            quality_level=QualityLevel.POOR,
        )

    def get_quality_report(self, days: int = 7) -> Dict:
        """Get quality report for recent runs."""
        # Get metrics from last N days
        cutoff = datetime.utcnow()
        metrics = self.db.query(QualityMetricsDB).filter(
            QualityMetricsDB.timestamp >= cutoff
        ).all()

        if not metrics:
            return {
                'total_runs': 0,
                'average_coverage': 0.0,
                'average_diversity': 0.0,
                'average_accuracy': 0.0,
                'quality_distribution': {},
            }

        avg_coverage = sum(m.coverage_score for m in metrics) / len(metrics)
        avg_diversity = sum(m.diversity_score for m in metrics) / len(metrics)
        avg_accuracy = sum(m.accuracy_score for m in metrics) / len(metrics)

        # Quality distribution
        quality_dist = {}
        for m in metrics:
            level = m.quality_level
            quality_dist[level] = quality_dist.get(level, 0) + 1

        return {
            'total_runs': len(metrics),
            'average_coverage': round(avg_coverage, 2),
            'average_diversity': round(avg_diversity, 2),
            'average_accuracy': round(avg_accuracy, 2),
            'quality_distribution': quality_dist,
            'recent_runs': [m.to_dict() for m in metrics[-10:]],
        }


class GatingService:
    """Service for recommendation gating and approval workflows."""

    def __init__(self, db: Session):
        """Initialize gating service."""
        self.db = db
        self.policies: Dict[str, GatingPolicy] = {}
        self._init_default_policies()

    def _init_default_policies(self):
        """Initialize default gating policies."""
        self.policies['strict'] = GatingPolicy(
            name='strict',
            min_score=80.0,
            min_coverage=0.7,
            require_approval=True,
        )
        self.policies['standard'] = GatingPolicy(
            name='standard',
            min_score=60.0,
            min_coverage=0.5,
            require_approval=False,
        )
        self.policies['permissive'] = GatingPolicy(
            name='permissive',
            min_score=40.0,
            min_coverage=0.3,
            require_approval=False,
        )

    def register_policy(self, policy: GatingPolicy):
        """Register a gating policy."""
        self.policies[policy.name] = policy

    def check_recommendation(self, reco: RecommendationItem,
                            policy_name: str = 'standard') -> Tuple[bool, List[str]]:
        """Check if recommendation passes gating policy."""
        policy = self.policies.get(policy_name)
        if not policy or not policy.enabled:
            return True, []

        issues = []

        # Score check
        if reco.recommendation_score < policy.min_score:
            issues.append(
                f"Score {reco.recommendation_score} below minimum {policy.min_score}"
            )
        if reco.recommendation_score > policy.max_score:
            issues.append(
                f"Score {reco.recommendation_score} above maximum {policy.max_score}"
            )

        # Compliance checks
        for rule in policy.compliance_rules:
            if not self._check_compliance_rule(reco, rule):
                issues.append(f"Compliance rule failed: {rule}")

        passed = len(issues) == 0
        return passed, issues

    def _check_compliance_rule(self, reco: RecommendationItem, rule: str) -> bool:
        """Check compliance rule."""
        # Custom compliance rules can be implemented here
        # Examples:
        # - No duplicate families in same customer
        # - No recently recommended products
        # - Budget level alignment
        return True

    def check_batch(self, recos: List[RecommendationItem],
                   policy_name: str = 'standard') -> Dict:
        """Check batch of recommendations."""
        passed = []
        failed = []

        for reco in recos:
            is_passed, issues = self.check_recommendation(reco, policy_name)
            if is_passed:
                passed.append(reco)
            else:
                failed.append({
                    'reco': reco,
                    'issues': issues,
                })

        return {
            'total': len(recos),
            'passed': len(passed),
            'failed': len(failed),
            'pass_rate': len(passed) / max(len(recos), 1),
            'failed_recommendations': failed,
        }
