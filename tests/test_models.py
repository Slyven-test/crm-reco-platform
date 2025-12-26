"""Tests for database models."""

import pytest
from datetime import date
from sqlalchemy.orm import Session

from core.db.models import (
    Product, ProductAlias, Customer, OrderLine, ContactEvent,
    ClientMasterProfile, RecoRun, RecoItem, AuditItem, OutcomeEvent
)


class TestProductModel:
    """Tests for Product model."""

    def test_create_product(self, db_session: Session):
        """Test creating a product."""
        product = Product(
            product_key="TEST_001",
            product_label="Test Wine",
            family_crm="Red",
            is_active=True,
        )
        db_session.add(product)
        db_session.commit()

        found = db_session.query(Product).filter_by(product_key="TEST_001").first()
        assert found is not None
        assert found.product_label == "Test Wine"
        assert found.family_crm == "Red"

    def test_product_with_aroma(self, db_session: Session):
        """Test product with full aroma profile."""
        product = Product(
            product_key="AROMA_TEST",
            product_label="Aroma Test",
            aroma_fruit=5,
            aroma_floral=4,
            aroma_spice=3,
            aroma_mineral=2,
            aroma_acidity=4,
            aroma_body=3,
            aroma_tannin=2,
        )
        db_session.add(product)
        db_session.commit()

        found = db_session.query(Product).filter_by(product_key="AROMA_TEST").first()
        assert found.aroma_fruit == 5
        assert found.aroma_body == 3


class TestProductAliasModel:
    """Tests for ProductAlias model."""

    def test_create_product_alias(self, db_session: Session, sample_product):
        """Test creating a product alias."""
        alias = ProductAlias(
            label_norm="test wine normal",
            product_key=sample_product.product_key,
        )
        db_session.add(alias)
        db_session.commit()

        found = db_session.query(ProductAlias).filter_by(
            label_norm="test wine normal"
        ).first()
        assert found is not None
        assert found.product_key == sample_product.product_key


class TestCustomerModel:
    """Tests for Customer model."""

    def test_create_customer(self, db_session: Session):
        """Test creating a customer."""
        customer = Customer(
            customer_code="CUST_TEST_001",
            last_name="Test",
            first_name="User",
            email="test@example.com",
            country="France",
            is_contactable=True,
        )
        db_session.add(customer)
        db_session.commit()

        found = db_session.query(Customer).filter_by(
            customer_code="CUST_TEST_001"
        ).first()
        assert found is not None
        assert found.email == "test@example.com"
        assert found.is_contactable is True

    def test_customer_contact_status(self, db_session: Session):
        """Test customer contact status flags."""
        customer = Customer(
            customer_code="BOUNCE_TEST",
            is_bounced=True,
            is_optout=False,
            is_contactable=False,
        )
        db_session.add(customer)
        db_session.commit()

        found = db_session.query(Customer).filter_by(
            customer_code="BOUNCE_TEST"
        ).first()
        assert found.is_bounced is True
        assert found.is_contactable is False


class TestOrderLineModel:
    """Tests for OrderLine model."""

    def test_create_order_line(self, db_session: Session, sample_customer, sample_product):
        """Test creating an order line."""
        order_line = OrderLine(
            customer_code=sample_customer.customer_code,
            product_key=sample_product.product_key,
            order_date=date(2025, 1, 15),
            doc_ref="INV_2025_001",
            qty=2.0,
            amount_ht=150.0,
            amount_ttc=180.0,
        )
        db_session.add(order_line)
        db_session.commit()

        found = db_session.query(OrderLine).filter_by(
            doc_ref="INV_2025_001"
        ).first()
        assert found is not None
        assert found.customer_code == sample_customer.customer_code
        assert found.amount_ht == 150.0
        assert found.qty == 2.0


class TestContactEventModel:
    """Tests for ContactEvent model."""

    def test_create_contact_event(self, db_session: Session, sample_customer):
        """Test creating a contact event."""
        event = ContactEvent(
            customer_code=sample_customer.customer_code,
            contact_date=date(2025, 1, 20),
            channel="EMAIL",
            status="SENT",
            campaign_id="CAMP_2025_01",
        )
        db_session.add(event)
        db_session.commit()

        found = db_session.query(ContactEvent).filter_by(
            campaign_id="CAMP_2025_01"
        ).first()
        assert found is not None
        assert found.channel == "EMAIL"
        assert found.status == "SENT"


class TestClientMasterProfileModel:
    """Tests for ClientMasterProfile model."""

    def test_create_master_profile(self, db_session: Session, sample_customer):
        """Test creating a master profile."""
        profile = ClientMasterProfile(
            customer_code=sample_customer.customer_code,
            premiere_date_achat=date(2023, 1, 1),
            derniere_date_achat=date(2025, 1, 20),
            recence_jours=5,
            nb_commandes=10,
            ca_ht=1500.0,
            r_score=4,
            f_score=4,
            m_score=5,
            rfm="445",
            segment="VIP",
            aroma_confidence=0.85,
            aroma_level="HIGH",
        )
        db_session.add(profile)
        db_session.commit()

        found = db_session.query(ClientMasterProfile).filter_by(
            customer_code=sample_customer.customer_code
        ).first()
        assert found is not None
        assert found.rfm == "445"
        assert found.segment == "VIP"
        assert found.aroma_level == "HIGH"


class TestRecoRunModel:
    """Tests for RecoRun model."""

    def test_create_reco_run(self, db_session: Session):
        """Test creating a recommendation run."""
        run = RecoRun(
            run_id="RUN_2025_01",
            config_hash="abc123def456",
            total_customers=1000,
            eligible_customers=950,
            exported_customers=945,
            duration_seconds=125.5,
        )
        db_session.add(run)
        db_session.commit()

        found = db_session.query(RecoRun).filter_by(run_id="RUN_2025_01").first()
        assert found is not None
        assert found.total_customers == 1000
        assert found.config_hash == "abc123def456"


class TestRecoItemModel:
    """Tests for RecoItem model."""

    def test_create_reco_item(
        self, db_session: Session, sample_customer, sample_product
    ):
        """Test creating a recommendation item."""
        run = RecoRun(
            run_id="RUN_TEST",
            config_hash="test123",
            total_customers=1,
            eligible_customers=1,
            exported_customers=1,
        )
        db_session.add(run)
        db_session.commit()

        reco = RecoItem(
            run_id=run.run_id,
            customer_code=sample_customer.customer_code,
            scenario="REBUY",
            rank=1,
            product_key=sample_product.product_key,
            score=0.95,
            explain_short="Based on purchase history",
        )
        db_session.add(reco)
        db_session.commit()

        found = db_session.query(RecoItem).filter_by(run_id=run.run_id).first()
        assert found is not None
        assert found.scenario == "REBUY"
        assert found.rank == 1
        assert found.score == 0.95


class TestAuditItemModel:
    """Tests for AuditItem model."""

    def test_create_audit_item(self, db_session: Session):
        """Test creating an audit item."""
        run = RecoRun(
            run_id="RUN_AUDIT_TEST",
            config_hash="test123",
            total_customers=1,
            eligible_customers=1,
            exported_customers=0,
        )
        db_session.add(run)
        db_session.commit()

        audit = AuditItem(
            run_id=run.run_id,
            customer_code="CUST_AUDIT",
            severity="ERROR",
            rule_code="SILENCE_WINDOW",
        )
        db_session.add(audit)
        db_session.commit()

        found = db_session.query(AuditItem).filter_by(
            rule_code="SILENCE_WINDOW"
        ).first()
        assert found is not None
        assert found.severity == "ERROR"


class TestOutcomeEventModel:
    """Tests for OutcomeEvent model."""

    def test_create_outcome_event(self, db_session: Session, sample_customer):
        """Test creating an outcome event."""
        outcome = OutcomeEvent(
            customer_code=sample_customer.customer_code,
            campaign_id="CAMP_2025_01",
            purchase_date=date(2025, 2, 1),
            revenue_ht=250.0,
            margin=75.0,
            last_touch_reco_rank=1,
        )
        db_session.add(outcome)
        db_session.commit()

        found = db_session.query(OutcomeEvent).filter_by(
            campaign_id="CAMP_2025_01"
        ).first()
        assert found is not None
        assert found.revenue_ht == 250.0
        assert found.last_touch_reco_rank == 1
