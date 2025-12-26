"""Score and rank recommendations."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text
import math

logger = logging.getLogger(__name__)


@dataclass
class RecoScore:
    """Score breakdown for a recommendation."""
    product_key: str
    scenario: str
    base_score: float  # 0-100
    affinity_score: float  # 0-100 (how related to customer preferences)
    popularity_score: float  # 0-100
    profit_score: float  # 0-100 (margin)
    final_score: float  # Weighted combination
    
    def to_dict(self) -> Dict:
        """Convert to dict."""
        return {
            'product_key': self.product_key,
            'scenario': self.scenario,
            'base_score': round(self.base_score, 2),
            'affinity_score': round(self.affinity_score, 2),
            'popularity_score': round(self.popularity_score, 2),
            'profit_score': round(self.profit_score, 2),
            'final_score': round(self.final_score, 2),
        }


class RecommendationScorer:
    """Score and rank recommendations."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
        # Weights for final score calculation
        self.weights = {
            'affinity': 0.40,  # Customer preference match
            'popularity': 0.30,  # Product popularity
            'profit': 0.20,  # Margin/profitability
            'base': 0.10,  # Base scenario fit
        }

    def compute_affinity_score(
        self,
        customer_code: str,
        product_key: str,
    ) -> float:
        """Compute how well product matches customer preferences.
        
        Factors:
        - Aroma axis alignment
        - Family preferences
        - Price range fit
        
        Args:
            customer_code: Customer code
            product_key: Product key
            
        Returns:
            Score 0-100
        """
        try:
            # Get customer's preferred families from purchases
            result = self.db.execute(text("""
                SELECT p.family
                FROM order_line ol
                JOIN product p ON ol.product_key = p.product_key
                WHERE ol.customer_code = :customer_code
                GROUP BY p.family
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """), {'customer_code': customer_code})
            
            preferred_family = result.fetchone()
            
            # Get product info
            result = self.db.execute(text("""
                SELECT family, aroma_axes, price_level
                FROM product
                WHERE product_key = :product_key
            """), {'product_key': product_key})
            
            product = result.fetchone()
            if not product:
                return 50.0  # Neutral score
            
            score = 50.0  # Base
            
            # Family match bonus
            if preferred_family and product[0] == preferred_family[0]:
                score += 25.0
            elif product[0]:  # Different family - slight boost
                score += 10.0
            
            return min(100.0, score)
        
        except Exception as e:
            logger.warning(f"Failed to compute affinity score: {str(e)}")
            return 50.0

    def compute_popularity_score(
        self,
        product_key: str,
    ) -> float:
        """Get product popularity score.
        
        Args:
            product_key: Product key
            
        Returns:
            Score 0-100
        """
        try:
            result = self.db.execute(text("""
                SELECT popularity_score
                FROM product
                WHERE product_key = :product_key
            """), {'product_key': product_key})
            
            row = result.fetchone()
            if not row:
                return 50.0
            
            # Scale 0-1 to 0-100
            return float(row[0]) * 100.0 if row[0] else 50.0
        
        except Exception as e:
            logger.warning(f"Failed to get popularity score: {str(e)}")
            return 50.0

    def compute_profit_score(
        self,
        product_key: str,
    ) -> float:
        """Compute profitability score based on margin.
        
        Args:
            product_key: Product key
            
        Returns:
            Score 0-100
        """
        try:
            # In real system, would fetch margin from product table
            # For now, use popularity as proxy
            result = self.db.execute(text("""
                SELECT popularity_score
                FROM product
                WHERE product_key = :product_key
            """), {'product_key': product_key})
            
            row = result.fetchone()
            if not row:
                return 50.0
            
            # Premium products have higher margins
            return float(row[0]) * 100.0 if row[0] else 50.0
        
        except Exception as e:
            logger.warning(f"Failed to compute profit score: {str(e)}")
            return 50.0

    def score_recommendation(
        self,
        customer_code: str,
        product_key: str,
        scenario: str,
        base_score: float = 80.0,  # Base score from scenario match
    ) -> RecoScore:
        """Compute complete recommendation score.
        
        Args:
            customer_code: Customer code
            product_key: Product key
            scenario: Recommendation scenario
            base_score: Base score from scenario match
            
        Returns:
            RecoScore with all components
        """
        affinity = self.compute_affinity_score(customer_code, product_key)
        popularity = self.compute_popularity_score(product_key)
        profit = self.compute_profit_score(product_key)
        
        # Weighted final score
        final_score = (
            self.weights['affinity'] * affinity +
            self.weights['popularity'] * popularity +
            self.weights['profit'] * profit +
            self.weights['base'] * base_score
        )
        
        return RecoScore(
            product_key=product_key,
            scenario=scenario,
            base_score=base_score,
            affinity_score=affinity,
            popularity_score=popularity,
            profit_score=profit,
            final_score=final_score,
        )

    def rank_recommendations(
        self,
        scores: List[RecoScore],
        max_recommendations: int = 3,
    ) -> List[RecoScore]:
        """Rank recommendations by score.
        
        Args:
            scores: List of RecoScore objects
            max_recommendations: Maximum recommendations to return
            
        Returns:
            Top N recommendations sorted by score
        """
        # Sort by final_score descending
        ranked = sorted(scores, key=lambda x: x.final_score, reverse=True)
        
        # Return top N
        return ranked[:max_recommendations]

    def diversify_recommendations(
        self,
        ranked_scores: List[RecoScore],
        max_recommendations: int = 3,
    ) -> List[RecoScore]:
        """Diversify recommendations to avoid too many from same family.
        
        Args:
            ranked_scores: Already ranked recommendations
            max_recommendations: Maximum to return
            
        Returns:
            Diversified top recommendations
        """
        try:
            if not ranked_scores:
                return []
            
            # Fetch product families
            families = {}
            for score in ranked_scores:
                result = self.db.execute(text("""
                    SELECT family FROM product WHERE product_key = :pk
                """), {'pk': score.product_key})
                row = result.fetchone()
                families[score.product_key] = row[0] if row else None
            
            # Select diverse recommendations
            selected = []
            used_families = set()
            
            for score in ranked_scores:
                family = families.get(score.product_key)
                
                # Always include first recommendation
                if not selected:
                    selected.append(score)
                    if family:
                        used_families.add(family)
                # For others, prefer different families
                elif family not in used_families:
                    selected.append(score)
                    used_families.add(family)
                elif len(selected) < max_recommendations:
                    # Fill remaining slots with same family if needed
                    selected.append(score)
                
                if len(selected) >= max_recommendations:
                    break
            
            return selected
        
        except Exception as e:
            logger.warning(f"Failed to diversify recommendations: {str(e)}")
            return ranked_scores[:max_recommendations]
