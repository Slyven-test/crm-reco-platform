"""Audit and quality models."""

from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional


class ApprovalStatus(str, Enum):
    """Recommendation approval status."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"


class QualityLevel(str, Enum):
    """Quality assessment level."""
    EXCELLENT = "EXCELLENT"  # >= 90%
    GOOD = "GOOD"  # 75-89%
    ACCEPTABLE = "ACCEPTABLE"  # 60-74%
    POOR = "POOR"  # < 60%


@dataclass
class QualityMetrics:
    """Quality metrics for recommendations."""
    run_id: str
    total_recommendations: int
    coverage_score: float  # % of customers with recommendations
    diversity_score: float  # % with diverse products (0-1)
    accuracy_score: float  # Estimated accuracy (0-1)
    avg_score: float  # Average recommendation score
    median_score: float  # Median recommendation score
    diversity_ratio: float  # Avg products per family
    quality_level: QualityLevel
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dict."""
        return {
            'run_id': self.run_id,
            'total_recommendations': self.total_recommendations,
            'coverage_score': round(self.coverage_score, 2),
            'diversity_score': round(self.diversity_score, 2),
            'accuracy_score': round(self.accuracy_score, 2),
            'avg_score': round(self.avg_score, 2),
            'median_score': round(self.median_score, 2),
            'diversity_ratio': round(self.diversity_ratio, 2),
            'quality_level': self.quality_level.value,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class AuditLog:
    """Audit log entry for recommendations."""
    audit_id: str
    run_id: str
    customer_code: str
    product_key: str
    scenario: str
    recommendation_score: float
    approval_status: ApprovalStatus
    approval_reason: Optional[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    compliance_checks: Dict[str, bool] = field(default_factory=dict)
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dict."""
        return {
            'audit_id': self.audit_id,
            'run_id': self.run_id,
            'customer_code': self.customer_code,
            'product_key': self.product_key,
            'scenario': self.scenario,
            'recommendation_score': round(self.recommendation_score, 2),
            'approval_status': self.approval_status.value,
            'approval_reason': self.approval_reason,
            'created_at': self.created_at.isoformat(),
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by,
            'compliance_checks': self.compliance_checks,
            'flags': self.flags,
        }


@dataclass
class GatingPolicy:
    """Gating policy for recommendations."""
    name: str
    min_score: float = 60.0  # Minimum recommendation score
    max_score: float = 100.0  # Maximum recommendation score
    min_coverage: float = 0.5  # Minimum coverage (50%)
    max_diversity_violations: int = 0  # Max duplicates in family
    require_approval: bool = False  # Require manual approval
    compliance_rules: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ComplianceCheck:
    """Compliance check result."""
    check_name: str
    passed: bool
    severity: str  # "INFO", "WARNING", "ERROR"
    message: str
    details: Optional[Dict] = None
