"""Outcomes & Feedback Models"""

from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List


class OutcomeStatus(str, Enum):
    """Recommendation outcome status"""
    PENDING = "PENDING"  # Waiting for customer interaction
    ACCEPTED = "ACCEPTED"  # Customer accepted recommendation
    REJECTED = "REJECTED"  # Customer rejected recommendation
    PURCHASED = "PURCHASED"  # Customer purchased the product
    NOT_PURCHASED = "NOT_PURCHASED"  # Customer didn't purchase
    RETURNED = "RETURNED"  # Customer returned the product


class OutcomeReason(str, Enum):
    """Reason for outcome"""
    PRICE_TOO_HIGH = "PRICE_TOO_HIGH"
    NOT_INTERESTED = "NOT_INTERESTED"
    QUALITY_CONCERN = "QUALITY_CONCERN"
    COMPETITOR_CHOICE = "COMPETITOR_CHOICE"
    ALREADY_OWNS = "ALREADY_OWNS"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    BETTER_ALTERNATIVE = "BETTER_ALTERNATIVE"
    SATISFIED = "SATISFIED"
    EXCELLENT = "EXCELLENT"


class FeedbackType(str, Enum):
    """Type of feedback"""
    SATISFACTION = "SATISFACTION"  # 1-5 stars
    QUALITY = "QUALITY"  # Product quality feedback
    RELEVANCE = "RELEVANCE"  # Recommendation relevance
    PRICE = "PRICE"  # Price feedback
    DELIVERY = "DELIVERY"  # Delivery experience
    CUSTOM = "CUSTOM"  # Free-text feedback


@dataclass
class OutcomeRecord:
    """Recommendation outcome record"""
    audit_id: str
    customer_code: str
    product_key: str
    recommendation_score: float
    status: OutcomeStatus
    reason: Optional[OutcomeReason] = None
    purchased: bool = False
    purchase_amount: Optional[float] = None
    purchase_date: Optional[datetime] = None
    returned_date: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class FeedbackRecord:
    """Customer feedback record"""
    customer_code: str
    product_key: str
    feedback_type: FeedbackType
    score: int  # 1-5 scale
    comment: Optional[str] = None
    sentiment: Optional[str] = None  # positive/neutral/negative
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class OutcomeMetrics:
    """Outcome analytics metrics"""
    total_recommendations: int
    total_outcomes: int
    acceptance_rate: float  # % accepted/not_rejected
    purchase_rate: float  # % of recommended that were purchased
    return_rate: float  # % of purchased that were returned
    average_satisfaction: float  # avg satisfaction rating
    revenue_impact: float  # total revenue from recommended products
    roi: float  # return on investment
    recommendations_with_feedback: int
    recommendations_with_outcomes: int
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class ModelPerformanceMetrics:
    """Model performance tracking"""
    recommendation_id: str
    actual_outcome: OutcomeStatus
    predicted_score: float
    confidence: float  # 0-1 confidence level
    error_margin: float  # prediction vs actual
    is_accurate: bool  # prediction was accurate
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class RetrainingTrigger:
    """Model retraining trigger event"""
    trigger_type: str  # e.g., "PERFORMANCE_DROP", "NEW_DATA_THRESHOLD"
    severity: str  # LOW, MEDIUM, HIGH
    reason: str
    metrics_before: dict
    metrics_after: dict
    recommended_action: str
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class ABTestResult:
    """A/B test result tracking"""
    test_id: str
    variant_a: str  # Original model version
    variant_b: str  # New model version
    total_users_a: int
    total_users_b: int
    conversion_a: float  # Conversion rate for A
    conversion_b: float  # Conversion rate for B
    revenue_a: float  # Total revenue from A
    revenue_b: float  # Total revenue from B
    confidence_level: float  # Statistical confidence
    winner: str  # Which variant won
    started_at: datetime = None
    ended_at: datetime = None
    created_at: datetime = None

    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.utcnow()
        if self.created_at is None:
            self.created_at = datetime.utcnow()
