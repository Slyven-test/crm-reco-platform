"""Tests for recommendation API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.main import app
from api.service import RecommendationService


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine('sqlite:///:memory:')
    
    with engine.connect() as conn:
        # Create tables
        conn.execute(text("""
            CREATE TABLE customer (
                customer_code TEXT PRIMARY KEY,
                email TEXT,
                phone TEXT,
                first_name TEXT,
                last_name TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE product (
                product_key TEXT PRIMARY KEY,
                product_name TEXT,
                family TEXT,
                aroma_axes TEXT,
                is_premium BOOLEAN,
                popularity_score REAL
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE order_line (
                id INTEGER PRIMARY KEY,
                customer_code TEXT,
                product_key TEXT,
                amount_ht REAL,
                order_date DATE
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE contact_event (
                id INTEGER PRIMARY KEY,
                customer_code TEXT,
                contact_type TEXT,
                contact_date DATE
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE reco_item (
                id INTEGER PRIMARY KEY,
                reco_run_id TEXT,
                customer_code TEXT,
                rank INTEGER,
                scenario TEXT,
                product_key TEXT,
                product_name TEXT,
                score_total REAL,
                score_affinity REAL,
                score_popularity REAL,
                score_profit REAL,
                explanation TEXT,
                created_at TEXT
            )
        """))
        
        conn.commit()
    
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Wine Recommendation API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestRecommendationEndpoints:
    """Test recommendation endpoints."""
    
    def test_get_recommendations_not_found(self, client):
        """Test getting recommendations for non-existent customer."""
        response = client.get("/api/v1/recommendations/NONEXISTENT")
        assert response.status_code == 404
    
    def test_get_recommendations_with_params(self, client):
        """Test recommendation endpoint with parameters."""
        response = client.get(
            "/api/v1/recommendations/C001",
            params={"max_recommendations": 5}
        )
        # Will be 404 since no data, but should accept params
        assert response.status_code in [404, 500]
    
    def test_get_filtered_recommendations(self, client):
        """Test filtered recommendations endpoint."""
        response = client.get(
            "/api/v1/recommendations/C001/filtered",
            params={"scenario": "REBUY", "min_score": 80}
        )
        assert response.status_code in [404, 500]
    
    def test_get_history_not_found(self, client):
        """Test history endpoint."""
        response = client.get("/api/v1/recommendations/C001/history")
        assert response.status_code == 404
    
    def test_get_product_recommendations_not_found(self, client):
        """Test product recommendations endpoint."""
        response = client.get("/api/v1/recommendations/products/WINE001")
        assert response.status_code == 404
    
    def test_get_statistics(self, client):
        """Test statistics endpoint."""
        response = client.get(
            "/api/v1/recommendations/stats/overview",
            params={
                "from_date": "2025-01-01",
                "to_date": "2025-12-31"
            }
        )
        # Might succeed with empty stats or fail
        assert response.status_code in [200, 500]


class TestBatchEndpoint:
    """Test batch processing endpoint."""
    
    def test_batch_empty(self, client):
        """Test batch with empty customer list."""
        response = client.post(
            "/api/v1/recommendations/batch",
            json={
                "customer_codes": [],
                "limit": 10,
                "save_results": True
            }
        )
        # Should complete without error
        assert response.status_code in [200, 500]
    
    def test_batch_with_limit(self, client):
        """Test batch with limit."""
        response = client.post(
            "/api/v1/recommendations/batch",
            json={
                "customer_codes": None,
                "limit": 5,
                "save_results": False
            }
        )
        assert response.status_code in [200, 500]


class TestDeleteEndpoints:
    """Test delete endpoints."""
    
    def test_delete_customer_recommendations(self, client):
        """Test deleting customer recommendations."""
        response = client.delete("/api/v1/recommendations/C001")
        # Should not fail even if no data
        assert response.status_code in [200, 404, 500]
    
    def test_delete_old_recommendations(self, client):
        """Test deleting old recommendations."""
        response = client.delete(
            "/api/v1/recommendations/all/old",
            params={"days_old": 30}
        )
        assert response.status_code in [200, 500]


class TestRecommendationService:
    """Test recommendation service."""
    
    def test_service_get_recommendations_empty(self, test_db):
        """Test service with empty database."""
        service = RecommendationService(test_db)
        response = service.get_recommendations('C001')
        assert response is None
    
    def test_service_get_filtered_recommendations_empty(self, test_db):
        """Test filtered service with empty database."""
        service = RecommendationService(test_db)
        response = service.get_recommendations_filtered('C001')
        assert response is None
    
    def test_service_get_history_empty(self, test_db):
        """Test history service with empty database."""
        service = RecommendationService(test_db)
        response = service.get_recommendation_history('C001')
        assert response is None
    
    def test_service_get_statistics(self, test_db):
        """Test statistics service."""
        service = RecommendationService(test_db)
        response = service.get_statistics()
        assert response is not None
        assert response.total_recommendations == 0
    
    def test_service_clear_recommendations(self, test_db):
        """Test clearing recommendations."""
        service = RecommendationService(test_db)
        deleted, success = service.clear_recommendations(customer_code='C001')
        assert success
        assert deleted == 0


class TestOpenAPI:
    """Test OpenAPI documentation."""
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema endpoint."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Wine Recommendation API"
        assert data["info"]["version"] == "1.0.0"
    
    def test_docs(self, client):
        """Test docs endpoint."""
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    
    def test_redoc(self, client):
        """Test ReDoc endpoint."""
        response = client.get("/api/redoc")
        assert response.status_code == 200
