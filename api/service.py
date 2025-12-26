"""Service layer for recommendation operations."""

import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.recommendation import RecommendationEngine
from api.models import (
    RecommendationResponse,
    RecommendationDetail,
    ScoreDetail,
    ExplanationDetail,
    HistoryResponse,
    HistoryItem,
    StatsResponse,
    ScenarioStats,
)

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for recommendation operations."""

    def __init__(self, db: Session):
        """Initialize service.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.engine = RecommendationEngine(db)

    def get_recommendations(
        self,
        customer_code: str,
        max_recommendations: int = 3,
    ) -> Optional[RecommendationResponse]:
        """Get recommendations for a customer.
        
        Args:
            customer_code: Customer code
            max_recommendations: Max recommendations to return
            
        Returns:
            RecommendationResponse or None if failed
        """
        logger.info(f"Getting recommendations for {customer_code}")
        
        try:
            result, success = self.engine.generate_recommendations(
                customer_code,
                max_recommendations=max_recommendations,
                enable_silence_check=True,
            )
            
            if not success or not result.recommendations:
                logger.warning(f"No recommendations for {customer_code}")
                return None
            
            # Convert to response model
            recommendations = []
            for item in result.recommendations:
                reco = RecommendationDetail(
                    rank=item.rank,
                    product_key=item.product_key,
                    product_name=item.product_key,  # Fetch actual name
                    scenario=item.scenario,
                    score=ScoreDetail(
                        base_score=item.score.base_score,
                        affinity_score=item.score.affinity_score,
                        popularity_score=item.score.popularity_score,
                        profit_score=item.score.profit_score,
                        final_score=item.score.final_score,
                    ),
                    explanation=ExplanationDetail(
                        title=item.explanation['title'],
                        reason=item.explanation['reason'],
                        components=item.explanation['components'],
                    ),
                )
                recommendations.append(reco)
            
            return RecommendationResponse(
                run_id=result.run_id,
                customer_code=customer_code,
                recommendations=recommendations,
                generated_at=result.generated_at,
                scenario_count=len(result.scenarios_matched),
            )
        
        except Exception as e:
            logger.error(f"Failed to get recommendations: {str(e)}")
            return None

    def get_recommendations_filtered(
        self,
        customer_code: str,
        scenario: Optional[str] = None,
        min_score: Optional[float] = None,
        limit: int = 3,
    ) -> Optional[RecommendationResponse]:
        """Get filtered recommendations.
        
        Args:
            customer_code: Customer code
            scenario: Filter by scenario
            min_score: Minimum score
            limit: Max results
            
        Returns:
            RecommendationResponse or None
        """
        response = self.get_recommendations(customer_code, max_recommendations=10)
        if not response:
            return None
        
        # Filter
        filtered = response.recommendations
        
        if scenario:
            filtered = [r for r in filtered if r.scenario == scenario]
        
        if min_score:
            filtered = [r for r in filtered if r.score.final_score >= min_score]
        
        # Limit
        filtered = filtered[:limit]
        
        if not filtered:
            return None
        
        response.recommendations = filtered
        return response

    def get_recommendation_history(
        self,
        customer_code: str,
        limit: int = 10,
    ) -> Optional[HistoryResponse]:
        """Get recommendation history for customer.
        
        Args:
            customer_code: Customer code
            limit: Max results
            
        Returns:
            HistoryResponse or None
        """
        try:
            result = self.db.execute(text("""
                SELECT DISTINCT reco_run_id, created_at, COUNT(*) as reco_count
                FROM reco_item
                WHERE customer_code = :customer_code
                GROUP BY reco_run_id, created_at
                ORDER BY created_at DESC
                LIMIT :limit
            """), {'customer_code': customer_code, 'limit': limit})
            
            rows = result.fetchall()
            if not rows:
                return None
            
            history = [
                HistoryItem(
                    run_id=row[0],
                    generated_at=row[1],
                    recommendations_count=row[2],
                )
                for row in rows
            ]
            
            return HistoryResponse(
                customer_code=customer_code,
                history=history,
            )
        
        except Exception as e:
            logger.error(f"Failed to get history: {str(e)}")
            return None

    def get_statistics(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Optional[StatsResponse]:
        """Get recommendation statistics.
        
        Args:
            from_date: Start date (ISO format)
            to_date: End date (ISO format)
            
        Returns:
            StatsResponse or None
        """
        try:
            # Build date filter
            date_filter = ""
            params = {}
            
            if from_date:
                date_filter += "AND DATE(created_at) >= :from_date "
                params['from_date'] = from_date
            
            if to_date:
                date_filter += "AND DATE(created_at) <= :to_date "
                params['to_date'] = to_date
            
            # Total recommendations
            result = self.db.execute(text(f"""
                SELECT COUNT(*) FROM reco_item
                WHERE 1=1 {date_filter}
            """), params)
            total_reco = result.scalar() or 0
            
            # Unique customers
            result = self.db.execute(text(f"""
                SELECT COUNT(DISTINCT customer_code) FROM reco_item
                WHERE 1=1 {date_filter}
            """), params)
            unique_customers = result.scalar() or 0
            
            # Scenario breakdown
            result = self.db.execute(text(f"""
                SELECT scenario, COUNT(*) as count, AVG(score_total) as avg_score
                FROM reco_item
                WHERE 1=1 {date_filter}
                GROUP BY scenario
                ORDER BY count DESC
            """), params)
            
            scenario_stats = []
            for row in result:
                stats = ScenarioStats(
                    scenario=row[0],
                    count=row[1],
                    avg_score=float(row[2]) if row[2] else 0.0,
                    top_products=[],  # Could compute if needed
                )
                scenario_stats.append(stats)
            
            # Average score
            result = self.db.execute(text(f"""
                SELECT AVG(score_total) FROM reco_item
                WHERE 1=1 {date_filter}
            """), params)
            avg_score = float(result.scalar() or 0.0)
            
            # Top products
            result = self.db.execute(text(f"""
                SELECT product_key, COUNT(*) as count
                FROM reco_item
                WHERE 1=1 {date_filter}
                GROUP BY product_key
                ORDER BY count DESC
                LIMIT 5
            """), params)
            top_products = [row[0] for row in result]
            
            return StatsResponse(
                total_recommendations=total_reco,
                unique_customers=unique_customers,
                scenario_breakdown=scenario_stats,
                avg_score=avg_score,
                top_products=top_products,
                date_range={
                    'from': from_date or 'beginning',
                    'to': to_date or 'now',
                },
            )
        
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return None

    def get_product_recommendations(
        self,
        product_key: str,
        limit: int = 10,
    ) -> Optional[List[Dict]]:
        """Get customers who were recommended a specific product.
        
        Args:
            product_key: Product key
            limit: Max results
            
        Returns:
            List of customer recommendations or None
        """
        try:
            result = self.db.execute(text("""
                SELECT customer_code, scenario, rank, score_total, created_at
                FROM reco_item
                WHERE product_key = :product_key
                ORDER BY created_at DESC
                LIMIT :limit
            """), {'product_key': product_key, 'limit': limit})
            
            rows = result.fetchall()
            if not rows:
                return None
            
            return [
                {
                    'customer_code': row[0],
                    'scenario': row[1],
                    'rank': row[2],
                    'score': float(row[3]),
                    'created_at': row[4].isoformat(),
                }
                for row in rows
            ]
        
        except Exception as e:
            logger.error(f"Failed to get product recommendations: {str(e)}")
            return None

    def clear_recommendations(
        self,
        customer_code: Optional[str] = None,
        days_old: Optional[int] = None,
    ) -> Tuple[int, bool]:
        """Clear recommendations from database.
        
        Args:
            customer_code: Specific customer, or None for all
            days_old: Delete older than N days, or None for all
            
        Returns:
            Tuple of (deleted_count, success)
        """
        try:
            query = "DELETE FROM reco_item WHERE 1=1"
            params = {}
            
            if customer_code:
                query += " AND customer_code = :customer_code"
                params['customer_code'] = customer_code
            
            if days_old:
                query += " AND DATE(created_at) <= DATE('now', :days_offset)"
                params['days_offset'] = f"-{days_old} days"
            
            result = self.db.execute(text(query), params)
            deleted = result.rowcount
            self.db.commit()
            
            logger.info(f"Deleted {deleted} recommendations")
            return deleted, True
        
        except Exception as e:
            logger.error(f"Failed to delete recommendations: {str(e)}")
            self.db.rollback()
            return 0, False
