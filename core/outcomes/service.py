"""Outcomes Service - Tracks recommendation outcomes and feedback"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from .models import (
    OutcomeStatus, OutcomeReason, FeedbackType,
    OutcomeRecord, FeedbackRecord, OutcomeMetrics,
    ModelPerformanceMetrics, RetrainingTrigger, ABTestResult
)


class OutcomesService:
    """Service for managing recommendation outcomes"""

    def __init__(self, db=None):
        self.db = db

    def record_outcome(
        self,
        audit_id: str,
        customer_code: str,
        product_key: str,
        recommendation_score: float,
        status: OutcomeStatus,
        reason: Optional[OutcomeReason] = None,
        purchased: bool = False,
        purchase_amount: Optional[float] = None,
    ) -> OutcomeRecord:
        """Record a recommendation outcome"""
        outcome = OutcomeRecord(
            audit_id=audit_id,
            customer_code=customer_code,
            product_key=product_key,
            recommendation_score=recommendation_score,
            status=status,
            reason=reason,
            purchased=purchased,
            purchase_amount=purchase_amount,
            purchase_date=datetime.utcnow() if purchased else None,
        )
        # Save to database
        if self.db:
            self.db.save_outcome(outcome)
        return outcome

    def record_feedback(
        self,
        customer_code: str,
        product_key: str,
        feedback_type: FeedbackType,
        score: int,
        comment: Optional[str] = None,
    ) -> FeedbackRecord:
        """Record customer feedback on recommendation"""
        # Determine sentiment from score
        if score >= 4:
            sentiment = "positive"
        elif score >= 3:
            sentiment = "neutral"
        else:
            sentiment = "negative"

        feedback = FeedbackRecord(
            customer_code=customer_code,
            product_key=product_key,
            feedback_type=feedback_type,
            score=score,
            comment=comment,
            sentiment=sentiment,
        )
        # Save to database
        if self.db:
            self.db.save_feedback(feedback)
        return feedback

    def compute_outcome_metrics(
        self,
        days: int = 7,
        customer_code: Optional[str] = None,
    ) -> OutcomeMetrics:
        """Compute outcome metrics for time period"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Fetch outcomes from database
        outcomes = self.db.get_outcomes(
            since=cutoff_date,
            customer_code=customer_code
        ) if self.db else []

        if not outcomes:
            return OutcomeMetrics(
                total_recommendations=0,
                total_outcomes=0,
                acceptance_rate=0.0,
                purchase_rate=0.0,
                return_rate=0.0,
                average_satisfaction=0.0,
                revenue_impact=0.0,
                roi=0.0,
                recommendations_with_feedback=0,
                recommendations_with_outcomes=0,
            )

        total = len(outcomes)
        accepted = len([o for o in outcomes if o.status != OutcomeStatus.REJECTED])
        purchased = len([o for o in outcomes if o.purchased])
        returned = len([o for o in outcomes if o.status == OutcomeStatus.RETURNED])
        revenue = sum(o.purchase_amount or 0 for o in outcomes if o.purchased)

        # Fetch feedback
        feedback = self.db.get_feedback(since=cutoff_date) if self.db else []
        avg_satisfaction = (
            sum(f.score for f in feedback) / len(feedback)
            if feedback else 0.0
        )

        return OutcomeMetrics(
            total_recommendations=total,
            total_outcomes=total,
            acceptance_rate=accepted / total if total > 0 else 0.0,
            purchase_rate=purchased / total if total > 0 else 0.0,
            return_rate=returned / purchased if purchased > 0 else 0.0,
            average_satisfaction=avg_satisfaction,
            revenue_impact=revenue,
            roi=(revenue - (total * 100)) / (total * 100) if total > 0 else 0.0,
            recommendations_with_feedback=len(set(f.product_key for f in feedback)),
            recommendations_with_outcomes=total,
        )

    def check_retraining_triggers(
        self,
        current_metrics: OutcomeMetrics,
        previous_metrics: Optional[OutcomeMetrics] = None,
    ) -> List[RetrainingTrigger]:
        """Check if retraining should be triggered based on metrics"""
        triggers = []

        if previous_metrics:
            # Check for performance drop
            if current_metrics.purchase_rate < previous_metrics.purchase_rate * 0.9:
                triggers.append(
                    RetrainingTrigger(
                        trigger_type="PERFORMANCE_DROP",
                        severity="HIGH",
                        reason="Purchase rate dropped by >10%",
                        metrics_before={
                            "purchase_rate": previous_metrics.purchase_rate
                        },
                        metrics_after={
                            "purchase_rate": current_metrics.purchase_rate
                        },
                        recommended_action="Retrain with recent data",
                    )
                )

            # Check for satisfaction drop
            if (current_metrics.average_satisfaction <
                    previous_metrics.average_satisfaction * 0.85):
                triggers.append(
                    RetrainingTrigger(
                        trigger_type="SATISFACTION_DROP",
                        severity="MEDIUM",
                        reason="Average satisfaction dropped",
                        metrics_before={
                            "avg_satisfaction": previous_metrics.average_satisfaction
                        },
                        metrics_after={
                            "avg_satisfaction": current_metrics.average_satisfaction
                        },
                        recommended_action="Analyze feedback for patterns",
                    )
                )

        # Check for high return rate
        if current_metrics.return_rate > 0.15:  # >15% returns
            triggers.append(
                RetrainingTrigger(
                    trigger_type="HIGH_RETURN_RATE",
                    severity="HIGH",
                    reason="Return rate exceeds 15%",
                    metrics_before={},
                    metrics_after={"return_rate": current_metrics.return_rate},
                    recommended_action="Investigate product quality issues",
                )
            )

        # Check for low acceptance rate
        if current_metrics.acceptance_rate < 0.5:  # <50% acceptance
            triggers.append(
                RetrainingTrigger(
                    trigger_type="LOW_ACCEPTANCE_RATE",
                    severity="MEDIUM",
                    reason="Acceptance rate below 50%",
                    metrics_before={},
                    metrics_after={"acceptance_rate": current_metrics.acceptance_rate},
                    recommended_action="Review recommendation relevance",
                )
            )

        return triggers

    def track_model_performance(
        self,
        recommendation_id: str,
        actual_outcome: OutcomeStatus,
        predicted_score: float,
        confidence: float,
    ) -> ModelPerformanceMetrics:
        """Track individual model prediction performance"""
        # Calculate error margin
        actual_score = 1.0 if actual_outcome == OutcomeStatus.PURCHASED else 0.0
        error_margin = abs(actual_score - predicted_score)
        is_accurate = error_margin < 0.2  # 20% threshold

        metric = ModelPerformanceMetrics(
            recommendation_id=recommendation_id,
            actual_outcome=actual_outcome,
            predicted_score=predicted_score,
            confidence=confidence,
            error_margin=error_margin,
            is_accurate=is_accurate,
        )

        if self.db:
            self.db.save_performance_metric(metric)
        return metric

    def create_ab_test(
        self,
        test_id: str,
        variant_a: str,
        variant_b: str,
        duration_days: int = 7,
    ) -> ABTestResult:
        """Create A/B test for model comparison"""
        return ABTestResult(
            test_id=test_id,
            variant_a=variant_a,
            variant_b=variant_b,
            total_users_a=0,
            total_users_b=0,
            conversion_a=0.0,
            conversion_b=0.0,
            revenue_a=0.0,
            revenue_b=0.0,
            confidence_level=0.0,
            winner="",
        )

    def update_ab_test_results(
        self,
        test_id: str,
        variant_a_outcomes: List[OutcomeRecord],
        variant_b_outcomes: List[OutcomeRecord],
    ) -> ABTestResult:
        """Update A/B test results with actual outcomes"""
        a_purchased = len([o for o in variant_a_outcomes if o.purchased])
        b_purchased = len([o for o in variant_b_outcomes if o.purchased])

        total_a = len(variant_a_outcomes)
        total_b = len(variant_b_outcomes)

        conversion_a = a_purchased / total_a if total_a > 0 else 0.0
        conversion_b = b_purchased / total_b if total_b > 0 else 0.0

        revenue_a = sum(o.purchase_amount or 0 for o in variant_a_outcomes if o.purchased)
        revenue_b = sum(o.purchase_amount or 0 for o in variant_b_outcomes if o.purchased)

        # Determine winner (higher conversion)
        winner = "variant_b" if conversion_b > conversion_a else "variant_a"

        # Calculate confidence (simplified chi-square)
        confidence = self._calculate_confidence(conversion_a, conversion_b, total_a, total_b)

        result = ABTestResult(
            test_id=test_id,
            variant_a="variant_a",
            variant_b="variant_b",
            total_users_a=total_a,
            total_users_b=total_b,
            conversion_a=conversion_a,
            conversion_b=conversion_b,
            revenue_a=revenue_a,
            revenue_b=revenue_b,
            confidence_level=confidence,
            winner=winner,
            ended_at=datetime.utcnow(),
        )

        if self.db:
            self.db.save_ab_test_result(result)
        return result

    @staticmethod
    def _calculate_confidence(
        p1: float, p2: float, n1: int, n2: int
    ) -> float:
        """Calculate statistical confidence between two proportions"""
        if n1 < 30 or n2 < 30:  # Minimum sample size
            return 0.0
        # Simplified Z-test confidence
        pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = (pooled * (1 - pooled) * (1/n1 + 1/n2)) ** 0.5
        z = abs(p1 - p2) / se if se > 0 else 0
        # Approximate confidence from Z score
        return min(0.99, z / 1.96)  # 95% confidence threshold
