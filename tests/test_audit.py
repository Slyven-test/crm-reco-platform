"""Tests for audit and quality management."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.audit.service import AuditService, QualityService, GatingService
from core.audit.models import (
    ApprovalStatus, QualityLevel, GatingPolicy, AuditLog
)
from core.audit.database import AuditLogDB, QualityMetricsDB
from core.database import Base, RecommendationItem


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    
    from core.audit.database import Base as AuditBase
    AuditBase.metadata.create_all(engine)
    
    db = Session(engine)
    yield db
    db.close()


class TestAuditService:
    """Test audit service."""

    def test_log_recommendation(self, test_db):
        """Test logging a recommendation."""
        audit_service = AuditService(test_db)
        
        audit = audit_service.log_recommendation(
            run_id='run-123',
            customer_code='C001',
            product_key='WINE001',
            scenario='REBUY',
            score=85.5,
        )
        
        assert audit.audit_id is not None
        assert audit.customer_code == 'C001'
        assert audit.product_key == 'WINE001'
        assert audit.recommendation_score == 85.5
        assert audit.approval_status == ApprovalStatus.PENDING

    def test_log_batch_recommendations(self, test_db):
        """Test logging batch recommendations."""
        audit_service = AuditService(test_db)
        
        recos = [
            {'customer_code': 'C001', 'product_key': 'WINE001', 'scenario': 'REBUY', 'score': 85.0},
            {'customer_code': 'C002', 'product_key': 'WINE002', 'scenario': 'UPSELL', 'score': 75.0},
            {'customer_code': 'C003', 'product_key': 'WINE003', 'scenario': 'CROSS_SELL', 'score': 80.0},
        ]
        
        logs = audit_service.log_batch_recommendations('run-123', recos)
        
        assert len(logs) == 3
        assert logs[0].customer_code == 'C001'
        assert logs[1].customer_code == 'C002'
        assert logs[2].customer_code == 'C003'

    def test_approve_recommendation(self, test_db):
        """Test approving a recommendation."""
        audit_service = AuditService(test_db)
        
        # First log
        audit = audit_service.log_recommendation(
            run_id='run-123',
            customer_code='C001',
            product_key='WINE001',
            scenario='REBUY',
            score=85.5,
        )
        
        # Approve
        success = audit_service.approve_recommendation(
            audit_id=audit.audit_id,
            approved_by='admin',
            reason='Good score and coverage'
        )
        
        assert success is True
        
        # Verify
        db_entry = test_db.query(AuditLogDB).filter(
            AuditLogDB.audit_id == audit.audit_id
        ).first()
        
        assert db_entry.approval_status == ApprovalStatus.APPROVED.value
        assert db_entry.approved_by == 'admin'
        assert db_entry.approval_reason == 'Good score and coverage'
        assert db_entry.approved_at is not None

    def test_reject_recommendation(self, test_db):
        """Test rejecting a recommendation."""
        audit_service = AuditService(test_db)
        
        audit = audit_service.log_recommendation(
            run_id='run-123',
            customer_code='C001',
            product_key='WINE001',
            scenario='REBUY',
            score=45.0,
        )
        
        success = audit_service.reject_recommendation(
            audit_id=audit.audit_id,
            approved_by='admin',
            reason='Score too low'
        )
        
        assert success is True
        
        db_entry = test_db.query(AuditLogDB).filter(
            AuditLogDB.audit_id == audit.audit_id
        ).first()
        
        assert db_entry.approval_status == ApprovalStatus.REJECTED.value

    def test_flag_recommendation(self, test_db):
        """Test flagging a recommendation."""
        audit_service = AuditService(test_db)
        
        audit = audit_service.log_recommendation(
            run_id='run-123',
            customer_code='C001',
            product_key='WINE001',
            scenario='REBUY',
            score=70.0,
        )
        
        success = audit_service.flag_recommendation(
            audit_id=audit.audit_id,
            flag_reason='Needs manual review'
        )
        
        assert success is True
        
        db_entry = test_db.query(AuditLogDB).filter(
            AuditLogDB.audit_id == audit.audit_id
        ).first()
        
        assert db_entry.approval_status == ApprovalStatus.FLAGGED.value
        assert 'Needs manual review' in db_entry.flags

    def test_get_pending_approvals(self, test_db):
        """Test getting pending approvals."""
        audit_service = AuditService(test_db)
        
        # Log some recommendations
        for i in range(3):
            audit_service.log_recommendation(
                run_id='run-123',
                customer_code=f'C{i:03d}',
                product_key=f'WINE{i:03d}',
                scenario='REBUY',
                score=70.0 + i * 5,
            )
        
        pending = audit_service.get_pending_approvals()
        
        assert len(pending) == 3
        assert pending[0]['approval_status'] == ApprovalStatus.PENDING.value

    def test_get_audit_history(self, test_db):
        """Test getting audit history for customer."""
        audit_service = AuditService(test_db)
        
        customer = 'C001'
        for i in range(5):
            audit_service.log_recommendation(
                run_id=f'run-{i}',
                customer_code=customer,
                product_key=f'WINE{i:03d}',
                scenario='REBUY',
                score=75.0,
            )
        
        history = audit_service.get_audit_history(customer)
        
        assert len(history) == 5
        assert all(h['customer_code'] == customer for h in history)


class TestQualityService:
    """Test quality service."""

    def test_compute_quality_metrics(self, test_db):
        """Test computing quality metrics."""
        # Create test recommendations
        for i in range(10):
            reco = RecommendationItem(
                recommendation_key=f'RECO{i:03d}',
                run_id='run-123',
                customer_code=f'C{i%5:03d}',
                product_key=f'WINE{i:03d}',
                scenario='REBUY',
                recommendation_score=70.0 + (i % 3) * 5,
                reason='Test',
            )
            test_db.add(reco)
        test_db.commit()
        
        quality_service = QualityService(test_db)
        metrics = quality_service.compute_quality_metrics('run-123', 100)
        
        assert metrics.total_recommendations == 10
        assert metrics.coverage_score > 0
        assert metrics.diversity_score >= 0
        assert metrics.accuracy_score > 0
        assert metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD, 
                                         QualityLevel.ACCEPTABLE, QualityLevel.POOR]

    def test_quality_level_excellent(self, test_db):
        """Test quality level excellent."""
        # Create high-quality recommendations
        for i in range(100):
            reco = RecommendationItem(
                recommendation_key=f'RECO{i:03d}',
                run_id='run-excellent',
                customer_code=f'C{i:03d}',
                product_key=f'WINE{i%50:03d}',
                scenario='REBUY',
                recommendation_score=85.0 + (i % 15),
                reason='Test',
            )
            test_db.add(reco)
        test_db.commit()
        
        quality_service = QualityService(test_db)
        metrics = quality_service.compute_quality_metrics('run-excellent', 100)
        
        # Should be excellent due to high coverage and accuracy
        assert metrics.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]

    def test_get_quality_report(self, test_db):
        """Test getting quality report."""
        quality_service = QualityService(test_db)
        
        # Create some recommendations for metrics
        for j in range(3):
            for i in range(20):
                reco = RecommendationItem(
                    recommendation_key=f'RECO{j}{i:03d}',
                    run_id=f'run-{j}',
                    customer_code=f'C{i%10:03d}',
                    product_key=f'WINE{i:03d}',
                    scenario='REBUY',
                    recommendation_score=75.0,
                    reason='Test',
                )
                test_db.add(reco)
            test_db.commit()
            
            # Compute metrics
            quality_service.compute_quality_metrics(f'run-{j}', 100)
        
        report = quality_service.get_quality_report(days=7)
        
        assert report['total_runs'] >= 0
        assert 'average_coverage' in report
        assert 'average_diversity' in report


class TestGatingService:
    """Test gating service."""

    def test_default_policies(self):
        """Test default policies are initialized."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        
        engine = create_engine('sqlite:///:memory:')
        db = Session(engine)
        
        gating = GatingService(db)
        
        assert 'strict' in gating.policies
        assert 'standard' in gating.policies
        assert 'permissive' in gating.policies

    def test_register_custom_policy(self):
        """Test registering custom gating policy."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        
        engine = create_engine('sqlite:///:memory:')
        db = Session(engine)
        
        gating = GatingService(db)
        
        custom_policy = GatingPolicy(
            name='custom',
            min_score=70.0,
            min_coverage=0.6,
        )
        
        gating.register_policy(custom_policy)
        
        assert 'custom' in gating.policies
        assert gating.policies['custom'].min_score == 70.0

    def test_check_recommendation_pass(self, test_db):
        """Test recommendation passing gating check."""
        # Create test recommendation
        reco = RecommendationItem(
            recommendation_key='RECO001',
            run_id='run-123',
            customer_code='C001',
            product_key='WINE001',
            scenario='REBUY',
            recommendation_score=85.0,
            reason='Test',
        )
        test_db.add(reco)
        test_db.commit()
        
        gating = GatingService(test_db)
        passed, issues = gating.check_recommendation(reco, 'standard')
        
        assert passed is True
        assert len(issues) == 0

    def test_check_recommendation_fail_low_score(self, test_db):
        """Test recommendation failing due to low score."""
        reco = RecommendationItem(
            recommendation_key='RECO001',
            run_id='run-123',
            customer_code='C001',
            product_key='WINE001',
            scenario='REBUY',
            recommendation_score=30.0,
            reason='Test',
        )
        test_db.add(reco)
        test_db.commit()
        
        gating = GatingService(test_db)
        passed, issues = gating.check_recommendation(reco, 'strict')
        
        assert passed is False
        assert any('Score' in issue for issue in issues)


class TestComplianceSummary:
    """Test compliance summary."""

    def test_compliance_counts(self, test_db):
        """Test compliance status counting."""
        audit_service = AuditService(test_db)
        
        # Log multiple recommendations with different statuses
        audit1 = audit_service.log_recommendation(
            run_id='run-123',
            customer_code='C001',
            product_key='WINE001',
            scenario='REBUY',
            score=85.0,
        )
        
        audit2 = audit_service.log_recommendation(
            run_id='run-123',
            customer_code='C002',
            product_key='WINE002',
            scenario='REBUY',
            score=75.0,
        )
        
        # Approve first, reject second
        audit_service.approve_recommendation(audit1.audit_id, 'admin')
        audit_service.reject_recommendation(audit2.audit_id, 'admin', 'Low score')
        
        # Query status counts
        from sqlalchemy import func
        status_counts = test_db.query(
            AuditLogDB.approval_status,
            func.count(AuditLogDB.audit_id).label('count')
        ).group_by(AuditLogDB.approval_status).all()
        
        status_dict = {status: count for status, count in status_counts}
        
        assert status_dict.get('APPROVED', 0) >= 1
        assert status_dict.get('REJECTED', 0) >= 1
