"""SQLAlchemy models for CRM recommendation platform."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from core.db.database import Base


class Product(Base):
    """Product dimension table."""
    __tablename__ = "product"

    product_key = Column(String(255), primary_key=True, index=True)
    product_label = Column(String(512), nullable=False, unique=True)
    family_crm = Column(String(255), nullable=True, index=True)
    cepage = Column(String(255), nullable=True)
    sucrosite_niveau = Column(String(50), nullable=True)
    price_band = Column(String(50), nullable=True)
    premium_tier = Column(Integer, nullable=True, default=0)
    
    # Aroma profile (7 axes, scale 1-5)
    aroma_fruit = Column(Integer, nullable=True)
    aroma_floral = Column(Integer, nullable=True)
    aroma_spice = Column(Integer, nullable=True)
    aroma_mineral = Column(Integer, nullable=True)
    aroma_acidity = Column(Integer, nullable=True)
    aroma_body = Column(Integer, nullable=True)
    aroma_tannin = Column(Integer, nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    season_tags = Column(JSON, nullable=True)  # ["summer", "christmas", ...]
    global_popularity_score = Column(Float, nullable=True, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product_aliases = relationship("ProductAlias", back_populates="product")
    order_lines = relationship("OrderLine", back_populates="product")

    __table_args__ = (
        Index("ix_product_family", "family_crm"),
        Index("ix_product_active", "is_active"),
    )


class ProductAlias(Base):
    """Mapping from normalized product labels to product keys."""
    __tablename__ = "product_alias"

    label_norm = Column(String(512), primary_key=True, index=True)
    product_key = Column(String(255), ForeignKey("product.product_key"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="product_aliases")


class Customer(Base):
    """Customer dimension table (clean, deduplicated)."""
    __tablename__ = "customer"

    customer_code = Column(String(255), primary_key=True, index=True)
    last_name = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    email = Column(String(512), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    postal_code = Column(String(20), nullable=True, index=True)
    city = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True, index=True)
    
    # Contact status
    is_bounced = Column(Boolean, default=False, index=True)
    is_optout = Column(Boolean, default=False, index=True)
    is_contactable = Column(Boolean, default=True, index=True)
    
    # Metadata
    batch_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order_lines = relationship("OrderLine", back_populates="customer")
    contact_events = relationship("ContactEvent", back_populates="customer")
    profiles = relationship("ClientMasterProfile", back_populates="customer")
    recommendations = relationship("RecoItem", back_populates="customer")

    __table_args__ = (
        Index("ix_customer_email", "email"),
        Index("ix_customer_batch", "batch_id"),
    )


class OrderLine(Base):
    """Normalized sales lines from customer transactions."""
    __tablename__ = "order_line"

    id = Column(BigInteger, primary_key=True)
    customer_code = Column(String(255), ForeignKey("customer.customer_code"), nullable=False, index=True)
    product_key = Column(String(255), ForeignKey("product.product_key"), nullable=False, index=True)
    
    order_date = Column(Date, nullable=False, index=True)
    doc_ref = Column(String(255), nullable=False, index=True)  # Invoice/Order reference
    doc_type = Column(String(50), nullable=True)  # "INVOICE", "ORDER", etc.
    
    qty = Column(Float, nullable=False, default=1.0)
    amount_ht = Column(Float, nullable=False)  # Amount HT (excluding tax)
    amount_ttc = Column(Float, nullable=True)  # Amount TTC (including tax)
    margin = Column(Float, nullable=True)
    
    batch_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="order_lines")
    product = relationship("Product", back_populates="order_lines")

    __table_args__ = (
        Index("ix_orderline_customer_date", "customer_code", "order_date"),
        Index("ix_orderline_product", "product_key"),
        Index("ix_orderline_doc", "doc_ref"),
    )


class ContactEvent(Base):
    """Contact history for silence window calculation."""
    __tablename__ = "contact_event"

    id = Column(BigInteger, primary_key=True)
    customer_code = Column(String(255), ForeignKey("customer.customer_code"), nullable=False, index=True)
    contact_date = Column(Date, nullable=False, index=True)
    channel = Column(String(50), nullable=True)  # "EMAIL", "SMS", "MAIL", etc.
    status = Column(String(50), nullable=True)  # "SENT", "OPENED", "BOUNCED", etc.
    campaign_id = Column(String(255), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="contact_events")

    __table_args__ = (
        Index("ix_contact_customer_date", "customer_code", "contact_date"),
    )


class ClientMasterProfile(Base):
    """Consolidated customer features and profile."""
    __tablename__ = "client_master_profile"

    id = Column(BigInteger, primary_key=True)
    customer_code = Column(String(255), ForeignKey("customer.customer_code"), nullable=False, index=True, unique=True)
    
    # RFM
    premiere_date_achat = Column(Date, nullable=True)
    derniere_date_achat = Column(Date, nullable=True, index=True)
    recence_jours = Column(Integer, nullable=True)
    nb_commandes = Column(Integer, nullable=True, default=0)
    ca_ht = Column(Float, nullable=True, default=0.0)
    r_score = Column(Integer, nullable=True)  # 1-5
    f_score = Column(Integer, nullable=True)  # 1-5
    m_score = Column(Integer, nullable=True)  # 1-5
    rfm = Column(String(10), nullable=True)  # e.g., "543"
    segment = Column(String(50), nullable=True, index=True)  # e.g., "VIP", "LOYAL"
    
    # Top preferences (family, grape, sugar, budget)
    top_family_1 = Column(String(255), nullable=True)
    top_family_1_ca_share = Column(Float, nullable=True)
    top_family_2 = Column(String(255), nullable=True)
    top_family_2_ca_share = Column(Float, nullable=True)
    family_diversity_score = Column(Float, nullable=True)
    
    top_grape_1 = Column(String(255), nullable=True)
    top_grape_1_ca_share = Column(Float, nullable=True)
    top_grape_2 = Column(String(255), nullable=True)
    top_grape_2_ca_share = Column(Float, nullable=True)
    
    top_sugar_1 = Column(String(50), nullable=True)
    top_sugar_1_ca_share = Column(Float, nullable=True)
    top_sugar_2 = Column(String(50), nullable=True)
    top_sugar_2_ca_share = Column(Float, nullable=True)
    
    top_budget_1 = Column(String(50), nullable=True)
    top_budget_1_ca_share = Column(Float, nullable=True)
    top_budget_2 = Column(String(50), nullable=True)
    top_budget_2_ca_share = Column(Float, nullable=True)
    
    # Aroma profile
    aroma_axe_1 = Column(String(50), nullable=True)
    aroma_score_1 = Column(Float, nullable=True)
    aroma_axe_2 = Column(String(50), nullable=True)
    aroma_score_2 = Column(Float, nullable=True)
    aroma_axe_3 = Column(String(50), nullable=True)
    aroma_score_3 = Column(Float, nullable=True)
    aroma_confidence = Column(Float, nullable=True)  # 0-1
    aroma_level = Column(String(20), nullable=True)  # "LOW", "MEDIUM", "HIGH"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="profiles")


class RecoRun(Base):
    """Metadata for each recommendation run."""
    __tablename__ = "reco_run"

    run_id = Column(String(255), primary_key=True, index=True)
    config_hash = Column(String(64), nullable=False)  # SHA256 of config
    code_version = Column(String(50), nullable=True)  # Git commit hash or version tag
    dataset_version = Column(String(50), nullable=True)
    run_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Run stats
    total_customers = Column(Integer, nullable=False, default=0)
    eligible_customers = Column(Integer, nullable=False, default=0)
    exported_customers = Column(Integer, nullable=False, default=0)
    
    # Timing
    duration_seconds = Column(Float, nullable=True)
    
    # Summary
    summary_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    recommendations = relationship("RecoItem", back_populates="run")
    audit_items = relationship("AuditItem", back_populates="run")


class RecoItem(Base):
    """Recommendation result for each customer."""
    __tablename__ = "reco_item"

    id = Column(BigInteger, primary_key=True)
    run_id = Column(String(255), ForeignKey("reco_run.run_id"), nullable=False, index=True)
    customer_code = Column(String(255), ForeignKey("customer.customer_code"), nullable=False, index=True)
    
    scenario = Column(String(50), nullable=False)  # "REBUY", "CROSS_SELL", etc.
    rank = Column(Integer, nullable=False)  # 1, 2, 3
    product_key = Column(String(255), ForeignKey("product.product_key"), nullable=False)
    
    score = Column(Float, nullable=False)
    explain_short = Column(String(512), nullable=True)
    reasons_json = Column(JSON, nullable=True)  # Breakdown of score components
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("RecoRun", back_populates="recommendations")
    customer = relationship("Customer", back_populates="recommendations")

    __table_args__ = (
        Index("ix_reco_run_customer", "run_id", "customer_code"),
        Index("ix_reco_rank", "rank"),
    )


class AuditItem(Base):
    """Audit flags and issues per recommendation."""
    __tablename__ = "audit_item"

    id = Column(BigInteger, primary_key=True)
    run_id = Column(String(255), ForeignKey("reco_run.run_id"), nullable=False, index=True)
    customer_code = Column(String(255), nullable=False, index=True)
    
    severity = Column(String(20), nullable=False)  # "ERROR", "WARN"
    rule_code = Column(String(100), nullable=False, index=True)  # "SILENCE_WINDOW", etc.
    details_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("RecoRun", back_populates="audit_items")

    __table_args__ = (
        Index("ix_audit_run_customer", "run_id", "customer_code"),
    )


class OutcomeEvent(Base):
    """Campaign outcomes for learning and attribution."""
    __tablename__ = "outcome_event"

    id = Column(BigInteger, primary_key=True)
    customer_code = Column(String(255), ForeignKey("customer.customer_code"), nullable=False, index=True)
    campaign_id = Column(String(255), nullable=False, index=True)
    
    purchase_date = Column(Date, nullable=True, index=True)
    revenue_ht = Column(Float, nullable=True)
    margin = Column(Float, nullable=True)
    
    # Attribution
    last_touch_reco_rank = Column(Integer, nullable=True)  # Which reco led to purchase
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_outcome_customer_campaign", "customer_code", "campaign_id"),
    )
