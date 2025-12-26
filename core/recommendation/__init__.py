"""Recommendation engine module."""

from core.recommendation.feature_computer import FeatureComputer
from core.recommendation.scenario_matcher import ScenarioMatcher, RecoScenario
from core.recommendation.scorer import RecommendationScorer, RecoScore
from core.recommendation.explanation_generator import ExplanationGenerator, Explanation
from core.recommendation.engine import (
    RecommendationEngine,
    RecommendationResult,
    RecommendationItem,
)

__all__ = [
    'FeatureComputer',
    'ScenarioMatcher',
    'RecoScenario',
    'RecommendationScorer',
    'RecoScore',
    'ExplanationGenerator',
    'Explanation',
    'RecommendationEngine',
    'RecommendationResult',
    'RecommendationItem',
]
