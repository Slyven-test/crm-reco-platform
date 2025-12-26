"""Main recommendation engine orchestrator."""

import logging
import uuid
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.recommendation.feature_computer import FeatureComputer
from core.recommendation.scenario_matcher import ScenarioMatcher, RecoScenario
from core.recommendation.scorer import RecommendationScorer, RecoScore
from core.recommendation.explanation_generator import ExplanationGenerator

logger = logging.getLogger(__name__)


class RecommendationItem:
    """A single recommendation for a customer."""

    def __init__(
        self,
        rank: int,
        product_key: str,
        scenario: str,
        score: RecoScore,
        explanation: Dict,
    ):
        self.rank = rank
        self.product_key = product_key
        self.scenario = scenario
        self.score = score
        self.explanation = explanation
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dict for serialization."""
        return {
            'rank': self.rank,
            'product_key': self.product_key,
            'scenario': self.scenario,
            'score': self.score.to_dict(),
            'explanation': self.explanation,
            'created_at': self.created_at.isoformat(),
        }


class RecommendationResult:
    """Result of recommendation generation."""

    def __init__(self, customer_code: str, run_id: str):
        self.customer_code = customer_code
        self.run_id = run_id
        self.recommendations: List[RecommendationItem] = []
        self.features: Dict = {}
        self.scenarios_matched: Dict = {}
        self.generated_at = datetime.utcnow()

    def add_recommendation(self, item: RecommendationItem):
        """Add a recommendation."""
        self.recommendations.append(item)

    def to_dict(self) -> Dict:
        """Convert to dict for serialization."""
        return {
            'run_id': self.run_id,
            'customer_code': self.customer_code,
            'generated_at': self.generated_at.isoformat(),
            'recommendations': [r.to_dict() for r in self.recommendations],
            'scenario_count': len(self.scenarios_matched),
        }


class RecommendationEngine:
    """Main recommendation engine."""

    def __init__(self, db: Session):
        """Initialize engine with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.feature_computer = FeatureComputer(db)
        self.scenario_matcher = ScenarioMatcher(db)
        self.scorer = RecommendationScorer(db)
        self.explanation_generator = ExplanationGenerator(db)

    def generate_recommendations(
        self,
        customer_code: str,
        max_recommendations: int = 3,
        enable_silence_check: bool = True,
    ) -> Tuple[RecommendationResult, bool]:
        """Generate recommendations for a customer.
        
        Pipeline:
        1. Compute customer features (RFM, preferences, budget)
        2. Match customer to scenarios (REBUY, CROSS_SELL, etc.)
        3. Score products in each scenario
        4. Rank and diversify
        5. Generate explanations
        6. Save to recommendation table
        
        Args:
            customer_code: Customer code
            max_recommendations: Max recommendations to return
            enable_silence_check: Check contact silence window
            
        Returns:
            Tuple of (result, success)
        """
        run_id = str(uuid.uuid4())
        logger.info(f"Starting recommendation generation for {customer_code} (run_id={run_id})")
        
        result = RecommendationResult(customer_code, run_id)
        
        try:
            # Step 1: Compute features
            logger.debug("Step 1: Computing customer features...")
            result.features = self.feature_computer.compute_customer_features(customer_code)
            
            # Check silence window
            if enable_silence_check:
                in_silence = self.feature_computer.get_silence_window(customer_code, days=30)
                if in_silence:
                    logger.info(f"Customer {customer_code} in silence window, skipping")
                    return result, False
            
            # Step 2: Match scenarios
            logger.debug("Step 2: Matching scenarios...")
            scenarios_match = self.scenario_matcher.match_scenarios(customer_code)
            
            if not scenarios_match:
                logger.warning(f"No scenarios matched for {customer_code}")
                return result, False
            
            result.scenarios_matched = {k.value: v for k, v in scenarios_match.items()}
            
            # Step 3: Score all products
            logger.debug("Step 3: Scoring recommendations...")
            all_scores: List[RecoScore] = []
            
            for scenario, products in scenarios_match.items():
                if not products:
                    continue
                
                for product_key in products:
                    # Scenario-specific base score
                    scenario_base_scores = {
                        RecoScenario.REBUY: 85.0,
                        RecoScenario.CROSS_SELL: 75.0,
                        RecoScenario.UPSELL: 80.0,
                        RecoScenario.WINBACK: 70.0,
                        RecoScenario.NURTURE: 65.0,
                    }
                    base_score = scenario_base_scores.get(scenario, 70.0)
                    
                    score = self.scorer.score_recommendation(
                        customer_code,
                        product_key,
                        scenario.value,
                        base_score=base_score,
                    )
                    all_scores.append(score)
            
            if not all_scores:
                logger.warning(f"No products scored for {customer_code}")
                return result, False
            
            # Step 4: Rank and diversify
            logger.debug("Step 4: Ranking and diversifying...")
            ranked = self.scorer.rank_recommendations(all_scores, max_recommendations)
            diversified = self.scorer.diversify_recommendations(ranked, max_recommendations)
            
            # Step 5: Generate explanations
            logger.debug("Step 5: Generating explanations...")
            for rank, score in enumerate(diversified, start=1):
                explanation = self.explanation_generator.generate_explanation(
                    customer_code,
                    score.product_key,
                    score.scenario,
                )
                
                item = RecommendationItem(
                    rank=rank,
                    product_key=score.product_key,
                    scenario=score.scenario,
                    score=score,
                    explanation=explanation.to_dict(),
                )
                result.add_recommendation(item)
            
            # Step 6: Save recommendations
            logger.debug("Step 6: Saving recommendations...")
            self._save_recommendations(result)
            
            logger.info(
                f"Generated {len(result.recommendations)} recommendations for {customer_code} "
                f"({len(result.scenarios_matched)} scenarios)"
            )
            return result, True
        
        except Exception as e:
            logger.error(f"Failed to generate recommendations for {customer_code}: {str(e)}")
            return result, False

    def _save_recommendations(self, result: RecommendationResult) -> None:
        """Save recommendations to database.
        
        Args:
            result: RecommendationResult object
        """
        try:
            for item in result.recommendations:
                # Get product name
                prod_result = self.db.execute(text("""
                    SELECT product_name FROM product WHERE product_key = :pk
                """), {'pk': item.product_key})
                prod_row = prod_result.fetchone()
                product_name = prod_row[0] if prod_row else item.product_key
                
                # Save to reco_item table
                self.db.execute(text("""
                    INSERT INTO reco_item
                    (reco_run_id, customer_code, rank, scenario, product_key, product_name,
                     score_total, score_affinity, score_popularity, score_profit,
                     explanation, created_at)
                    VALUES
                    (:run_id, :customer_code, :rank, :scenario, :product_key, :product_name,
                     :score_total, :score_affinity, :score_popularity, :score_profit,
                     :explanation, :created_at)
                """), {
                    'run_id': result.run_id,
                    'customer_code': result.customer_code,
                    'rank': item.rank,
                    'scenario': item.scenario,
                    'product_key': item.product_key,
                    'product_name': product_name,
                    'score_total': item.score.final_score,
                    'score_affinity': item.score.affinity_score,
                    'score_popularity': item.score.popularity_score,
                    'score_profit': item.score.profit_score,
                    'explanation': item.explanation['reason'],
                    'created_at': item.created_at,
                })
            
            self.db.commit()
            logger.debug(f"Saved {len(result.recommendations)} recommendations")
        
        except Exception as e:
            logger.warning(f"Failed to save recommendations: {str(e)}")
            self.db.rollback()

    def generate_batch_recommendations(
        self,
        customer_codes: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Tuple[RecommendationResult, bool]]:
        """Generate recommendations for batch of customers.
        
        Args:
            customer_codes: Specific customer codes, or None for all
            limit: Maximum customers to process
            
        Returns:
            Dict of {customer_code: (result, success)}
        """
        logger.info("Starting batch recommendation generation")
        
        # Get customer list
        if customer_codes:
            codes = customer_codes
        else:
            result = self.db.execute(text("""
                SELECT DISTINCT customer_code FROM customer LIMIT :limit
            """), {'limit': limit or 100000})
            codes = [row[0] for row in result]
        
        logger.info(f"Processing {len(codes)} customers")
        
        results = {}
        successes = 0
        
        for customer_code in codes:
            reco_result, success = self.generate_recommendations(customer_code)
            results[customer_code] = (reco_result, success)
            if success:
                successes += 1
        
        logger.info(f"Batch complete: {successes}/{len(codes)} successful")
        return results
