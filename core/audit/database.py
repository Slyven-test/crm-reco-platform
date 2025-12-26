"""Database models for audit and quality management."""

from datetime import datetime
from sqlalchemy import (
    Column, String, Float, DateTime, Boolean, Text, Integer, JSON
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuditLogDB(Base):
    """Audit log database model."""
    __tablename__ = 'audit_log'

    audit_id = Column(String(36), primary_key=True)
    run_id = Column(String(36), nullable=False, index=True)
    customer_code = Column(String(50), nullable=False, index=True)
    product_key = Column(String(50), nullable=False)
    scenario = Column(String(50), nullable=False)
    recommendation_score = Column(Float, nullable=False)
    approval_status = Column(String(20), nullable=False, default='PENDING')
    approval_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)
    compliance_checks = Column(JSON, nullable=True, default={})
    flags = Column(JSON, nullable=True, default=[])

    def to_dict(self):
        """Convert to dict."""
        return {
            'audit_id': self.audit_id,
            'run_id': self.run_id,
            'customer_code': self.customer_code,
            'product_key': self.product_key,
            'scenario': self.scenario,
            'recommendation_score': round(self.recommendation_score, 2),
            'approval_status': self.approval_status,
            'approval_reason': self.approval_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by,
            'compliance_checks': self.compliance_checks or {},
            'flags': self.flags or [],
        }


class QualityMetricsDB(Base):
    """Quality metrics database model."""
    __tablename__ = 'quality_metrics'

    run_id = Column(String(36), primary_key=True)
    total_recommendations = Column(Integer, nullable=False)
    coverage_score = Column(Float, nullable=False)
    diversity_score = Column(Float, nullable=False)
    accuracy_score = Column(Float, nullable=False)
    avg_score = Column(Float, nullable=False)
    median_score = Column(Float, nullable=False)
    quality_level = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_dict(self):
        """Convert to dict."""
        return {
            'run_id': self.run_id,
            'total_recommendations': self.total_recommendations,
            'coverage_score': round(self.coverage_score, 2),
            'diversity_score': round(self.diversity_score, 2),
            'accuracy_score': round(self.accuracy_score, 2),
            'avg_score': round(self.avg_score, 2),
            'median_score': round(self.median_score, 2),
            'quality_level': self.quality_level,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class ApprovalWorkflowDB(Base):
    """Approval workflow database model."""
    __tablename__ = 'approval_workflows'

    workflow_id = Column(String(36), primary_key=True)
    run_id = Column(String(36), nullable=False, index=True)
    audit_id = Column(String(36), nullable=False, index=True)
    status = Column(String(20), nullable=False, default='PENDING')
    requested_by = Column(String(100), nullable=False)
    approved_by = Column(String(100), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    approval_deadline = Column(DateTime, nullable=True)
    priority = Column(String(20), default='NORMAL')  # LOW, NORMAL, HIGH
    notes = Column(Text, nullable=True)

    def to_dict(self):
        """Convert to dict."""
        return {
            'workflow_id': self.workflow_id,
            'run_id': self.run_id,
            'audit_id': self.audit_id,
            'status': self.status,
            'requested_by': self.requested_by,
            'approved_by': self.approved_by,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'approval_deadline': self.approval_deadline.isoformat() if self.approval_deadline else None,
            'priority': self.priority,
            'notes': self.notes,
        }
