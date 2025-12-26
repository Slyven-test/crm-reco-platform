"""Pytest configuration and fixtures for testing."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from core.db.database import Base
from core.db.models import (
    Product, ProductAlias, Customer, OrderLine, ContactEvent,
    ClientMasterProfile, RecoRun, RecoItem, AuditItem, OutcomeEvent
)


@pytest.fixture(scope="session")
def test_db_url():
    """Provide test database URL."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine(test_db_url):
    """Create test database engine."""
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    """Provide a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_product(db_session):
    """Create sample product for testing."""
    product = Product(
        product_key="PINOT_NOIR_2022",
        product_label="Pinot Noir 2022",
        family_crm="Red",
        cepage="Pinot Noir",
        sucrosite_niveau="Dry",
        price_band="Mid",
        premium_tier=1,
        aroma_fruit=4,
        aroma_floral=3,
        aroma_spice=3,
        aroma_mineral=2,
        aroma_acidity=3,
        aroma_body=3,
        aroma_tannin=3,
        is_active=True,
        is_archived=False,
        global_popularity_score=0.8,
    )
    db_session.add(product)
    db_session.commit()
    return product


@pytest.fixture
def sample_customer(db_session):
    """Create sample customer for testing."""
    customer = Customer(
        customer_code="CUST_001",
        last_name="Dupont",
        first_name="Jean",
        email="jean.dupont@example.com",
        phone="+33612345678",
        address="123 Rue de Paris",
        postal_code="75001",
        city="Paris",
        country="France",
        is_bounced=False,
        is_optout=False,
        is_contactable=True,
    )
    db_session.add(customer)
    db_session.commit()
    return customer


@pytest.fixture
def sample_product_alias(db_session, sample_product):
    """Create sample product alias for testing."""
    alias = ProductAlias(
        label_norm="pinot noir 2022",
        product_key=sample_product.product_key,
    )
    db_session.add(alias)
    db_session.commit()
    return alias


pytest.mark.database = pytest.mark.database
