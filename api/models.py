"""Pydantic models for API requests and responses."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class ScoreDetail(BaseModel):
    """Score breakdown for a recommendation."""
    base_score: float = Field(..., ge=0, le=100, description="Base scenario score")
    affinity_score: float = Field(..., ge=0, le=100, description="Preference match score")
    popularity_score: float = Field(..., ge=0, le=100, description="Product popularity score")
    profit_score: float = Field(..., ge=0, le=100, description="Profitability score")
    final_score: float = Field(..., ge=0, le=100, description="Weighted final score")


class ExplanationDetail(BaseModel):
    """Explanation for a recommendation."""
    title: str = Field(..., description="Short explanation title")
    reason: str = Field(..., description="Why recommended")
    components: List[str] = Field(..., description="List of reason components")


class RecommendationDetail(BaseModel):
    """Single recommendation."""
    rank: int = Field(..., ge=1, description="Recommendation rank (1, 2, 3, ...)")
    product_key: str = Field(..., description="Product identifier")
    product_name: Optional[str] = Field(None, description="Product name")
    scenario: str = Field(..., description="Recommendation scenario")
    score: ScoreDetail = Field(..., description="Score breakdown")
    explanation: ExplanationDetail = Field(..., description="Explanation")


class RecommendationResponse(BaseModel):
    """Response for recommendation request."""
    run_id: str = Field(..., description="Unique run ID")
    customer_code: str = Field(..., description="Customer code")
    recommendations: List[RecommendationDetail] = Field(..., description="List of recommendations")
    generated_at: datetime = Field(..., description="Generation timestamp")
    scenario_count: int = Field(..., description="Number of scenarios matched")


class BatchRecommendationRequest(BaseModel):
    """Request for batch recommendations."""
    customer_codes: Optional[List[str]] = Field(None, description="Specific customers, or None for all")
    limit: Optional[int] = Field(100, ge=1, le=10000, description="Max customers to process")
    save_results: bool = Field(True, description="Save to database")


class BatchRecommendationResponse(BaseModel):
    """Response for batch recommendations."""
    total: int = Field(..., description="Total customers processed")
    successful: int = Field(..., description="Successful generations")
    failed: int = Field(..., description="Failed generations")
    duration_seconds: float = Field(..., description="Total duration")
    run_ids: List[str] = Field(..., description="Run IDs generated")


class FilterRequest(BaseModel):
    """Request to filter recommendations."""
    customer_code: str = Field(..., description="Customer code")
    scenario: Optional[str] = Field(None, description="Filter by scenario")
    min_score: Optional[float] = Field(None, ge=0, le=100, description="Minimum score")
    limit: int = Field(3, ge=1, le=10, description="Max results")


class HistoryRequest(BaseModel):
    """Request for recommendation history."""
    customer_code: str = Field(..., description="Customer code")
    limit: int = Field(10, ge=1, le=100, description="Max results")


class HistoryItem(BaseModel):
    """Single history item."""
    run_id: str
    generated_at: datetime
    recommendations_count: int


class HistoryResponse(BaseModel):
    """Response for history request."""
    customer_code: str
    history: List[HistoryItem]


class StatsRequest(BaseModel):
    """Request for statistics."""
    from_date: Optional[str] = Field(None, description="ISO date format YYYY-MM-DD")
    to_date: Optional[str] = Field(None, description="ISO date format YYYY-MM-DD")


class ScenarioStats(BaseModel):
    """Statistics for a scenario."""
    scenario: str
    count: int
    avg_score: float
    top_products: List[str]


class StatsResponse(BaseModel):
    """Response for statistics request."""
    total_recommendations: int
    unique_customers: int
    scenario_breakdown: List[ScenarioStats]
    avg_score: float
    top_products: List[str]
    date_range: Dict[str, str]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional details")
    code: Optional[str] = Field(None, description="Error code")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database status")
    timestamp: datetime = Field(..., description="Check timestamp")
