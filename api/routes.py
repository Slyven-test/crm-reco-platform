"""FastAPI routes for recommendation endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from api.models import (
    RecommendationResponse,
    BatchRecommendationRequest,
    BatchRecommendationResponse,
    FilterRequest,
    HistoryRequest,
    HistoryResponse,
    StatsRequest,
    StatsResponse,
    ErrorResponse,
)
from api.service import RecommendationService
from core.recommendation import RecommendationEngine

logger = logging.getLogger(__name__)

# Router for recommendation endpoints
router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


def get_db() -> Session:
    """Dependency to get database session.
    
    This should be replaced with actual database connection.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # This is a placeholder - replace with actual connection
    engine = create_engine('sqlite:///:memory:')
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


# ============================================================================
# GET Endpoints
# ============================================================================

@router.get(
    "/{customer_code}",
    response_model=RecommendationResponse,
    summary="Get Recommendations",
    description="Generate recommendations for a customer",
    responses={
        200: {"description": "Recommendations generated successfully"},
        404: {"description": "Customer not found or no recommendations"},
        500: {"description": "Internal server error"},
    },
)
async def get_recommendations(
    customer_code: str,
    max_recommendations: int = Query(3, ge=1, le=10, description="Max recommendations"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Get recommendations for a customer.
    
    Args:
        customer_code: Customer identifier
        max_recommendations: Maximum recommendations to return (1-10, default 3)
        
    Returns:
        RecommendationResponse with scored recommendations
        
    Raises:
        HTTPException: If customer not found or generation fails
    """
    logger.info(f"GET /recommendations/{customer_code}")
    
    service = RecommendationService(db)
    response = service.get_recommendations(
        customer_code,
        max_recommendations=max_recommendations,
    )
    
    if not response:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for customer {customer_code}",
        )
    
    return response


@router.get(
    "/{customer_code}/filtered",
    response_model=RecommendationResponse,
    summary="Get Filtered Recommendations",
    description="Get recommendations with filters applied",
)
async def get_filtered_recommendations(
    customer_code: str,
    scenario: Optional[str] = Query(None, description="Filter by scenario"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum score"),
    limit: int = Query(3, ge=1, le=10, description="Max results"),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Get filtered recommendations.
    
    Args:
        customer_code: Customer identifier
        scenario: Filter by scenario (REBUY, CROSS_SELL, UPSELL, WINBACK, NURTURE)
        min_score: Minimum recommendation score (0-100)
        limit: Maximum results to return
        
    Returns:
        RecommendationResponse with filtered recommendations
    """
    logger.info(f"GET /recommendations/{customer_code}/filtered?scenario={scenario}&min_score={min_score}")
    
    service = RecommendationService(db)
    response = service.get_recommendations_filtered(
        customer_code,
        scenario=scenario,
        min_score=min_score,
        limit=limit,
    )
    
    if not response:
        raise HTTPException(
            status_code=404,
            detail="No recommendations match the filter criteria",
        )
    
    return response


@router.get(
    "/{customer_code}/history",
    response_model=HistoryResponse,
    summary="Get Recommendation History",
    description="Get past recommendations for a customer",
)
async def get_history(
    customer_code: str,
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """Get recommendation history.
    
    Args:
        customer_code: Customer identifier
        limit: Maximum history items to return
        
    Returns:
        HistoryResponse with past recommendations
    """
    logger.info(f"GET /recommendations/{customer_code}/history")
    
    service = RecommendationService(db)
    response = service.get_recommendation_history(
        customer_code,
        limit=limit,
    )
    
    if not response:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for customer {customer_code}",
        )
    
    return response


@router.get(
    "/products/{product_key}",
    summary="Get Product Recommendations",
    description="Get customers recommended a specific product",
)
async def get_product_recommendations(
    product_key: str,
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    db: Session = Depends(get_db),
):
    """Get customers recommended a product.
    
    Args:
        product_key: Product identifier
        limit: Maximum results to return
        
    Returns:
        List of customers with their recommendation details
    """
    logger.info(f"GET /recommendations/products/{product_key}")
    
    service = RecommendationService(db)
    results = service.get_product_recommendations(product_key, limit=limit)
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for product {product_key}",
        )
    
    return {"product_key": product_key, "recommendations": results}


@router.get(
    "/stats/overview",
    response_model=StatsResponse,
    summary="Get Statistics",
    description="Get recommendation statistics",
)
async def get_statistics(
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
) -> StatsResponse:
    """Get recommendation statistics.
    
    Args:
        from_date: Start date (ISO format YYYY-MM-DD)
        to_date: End date (ISO format YYYY-MM-DD)
        
    Returns:
        StatsResponse with aggregated statistics
    """
    logger.info(f"GET /stats/overview?from_date={from_date}&to_date={to_date}")
    
    service = RecommendationService(db)
    response = service.get_statistics(from_date, to_date)
    
    if not response:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve statistics",
        )
    
    return response


# ============================================================================
# POST Endpoints
# ============================================================================

@router.post(
    "/batch",
    response_model=BatchRecommendationResponse,
    summary="Batch Generation",
    description="Generate recommendations for multiple customers",
)
async def generate_batch(
    request: BatchRecommendationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> BatchRecommendationResponse:
    """Generate recommendations for batch of customers.
    
    Args:
        request: Batch request with customer codes and limit
        background_tasks: FastAPI background tasks
        
    Returns:
        BatchRecommendationResponse with summary
    """
    logger.info(f"POST /recommendations/batch - {len(request.customer_codes or [])} customers")
    
    start_time = datetime.utcnow()
    engine = RecommendationEngine(db)
    
    results = engine.generate_batch_recommendations(
        customer_codes=request.customer_codes,
        limit=request.limit,
    )
    
    successful = sum(1 for _, success in results.values() if success)
    failed = len(results) - successful
    duration = (datetime.utcnow() - start_time).total_seconds()
    run_ids = list(results.keys())
    
    return BatchRecommendationResponse(
        total=len(results),
        successful=successful,
        failed=failed,
        duration_seconds=duration,
        run_ids=run_ids,
    )


# ============================================================================
# DELETE Endpoints
# ============================================================================

@router.delete(
    "/{customer_code}",
    summary="Delete Recommendations",
    description="Delete recommendations for a customer",
)
async def delete_recommendations(
    customer_code: str,
    db: Session = Depends(get_db),
):
    """Delete recommendations for a customer.
    
    Args:
        customer_code: Customer identifier
        
    Returns:
        Response with deletion status
    """
    logger.info(f"DELETE /recommendations/{customer_code}")
    
    service = RecommendationService(db)
    deleted, success = service.clear_recommendations(customer_code=customer_code)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete recommendations",
        )
    
    return {
        "status": "deleted",
        "customer_code": customer_code,
        "deleted_count": deleted,
    }


@router.delete(
    "/all/old",
    summary="Delete Old Recommendations",
    description="Delete recommendations older than N days",
)
async def delete_old_recommendations(
    days_old: int = Query(30, ge=1, description="Delete older than N days"),
    db: Session = Depends(get_db),
):
    """Delete old recommendations.
    
    Args:
        days_old: Delete recommendations older than N days
        
    Returns:
        Response with deletion status
    """
    logger.info(f"DELETE /recommendations/all/old?days_old={days_old}")
    
    service = RecommendationService(db)
    deleted, success = service.clear_recommendations(days_old=days_old)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete recommendations",
        )
    
    return {
        "status": "deleted",
        "days_old": days_old,
        "deleted_count": deleted,
    }


# ============================================================================
# Health Check
# ============================================================================

@router.get(
    "/health",
    summary="Health Check",
    description="Check API health status",
)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint.
    
    Returns:
        Health status response
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }
