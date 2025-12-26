"""Initial database schema creation.

Revision ID: 001
Revises: None
Create Date: 2025-12-26

Creates all core tables:
- Product and ProductAlias
- Customer and related contact/order tables
- ClientMasterProfile for consolidated features
- RecoRun, RecoItem, AuditItem for recommendations
- OutcomeEvent for campaign tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""
    
    # Product table
    op.create_table(
        'product',
        sa.Column('product_key', sa.String(255), nullable=False),
        sa.Column('product_label', sa.String(512), nullable=False),
        sa.Column('family_crm', sa.String(255), nullable=True),
        sa.Column('cepage', sa.String(255), nullable=True),
        sa.Column('sucrosite_niveau', sa.String(50), nullable=True),
        sa.Column('price_band', sa.String(50), nullable=True),
        sa.Column('premium_tier', sa.Integer(), nullable=True),
        sa.Column('aroma_fruit', sa.Integer(), nullable=True),
        sa.Column('aroma_floral', sa.Integer(), nullable=True),
        sa.Column('aroma_spice', sa.Integer(), nullable=True),
        sa.Column('aroma_mineral', sa.Integer(), nullable=True),
        sa.Column('aroma_acidity', sa.Integer(), nullable=True),
        sa.Column('aroma_body', sa.Integer(), nullable=True),
        sa.Column('aroma_tannin', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('season_tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('global_popularity_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('product_key'),
        sa.UniqueConstraint('product_label'),
    )
    op.create_index('ix_product_family', 'product', ['family_crm'])
    op.create_index('ix_product_active', 'product', ['is_active'])
    
    # ProductAlias table
    op.create_table(
        'product_alias',
        sa.Column('label_norm', sa.String(512), nullable=False),
        sa.Column('product_key', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['product_key'], ['product.product_key']),
        sa.PrimaryKeyConstraint('label_norm'),
    )
    op.create_index('ix_product_alias_label_norm', 'product_alias', ['label_norm'])
    
    # Customer table
    op.create_table(
        'customer',
        sa.Column('customer_code', sa.String(255), nullable=False),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(512), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('city', sa.String(255), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('is_bounced', sa.Boolean(), nullable=False),
        sa.Column('is_optout', sa.Boolean(), nullable=False),
        sa.Column('is_contactable', sa.Boolean(), nullable=False),
        sa.Column('batch_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('customer_code'),
    )
    op.create_index('ix_customer_email', 'customer', ['email'])
    op.create_index('ix_customer_postal_code', 'customer', ['postal_code'])
    op.create_index('ix_customer_country', 'customer', ['country'])
    op.create_index('ix_customer_batch_id', 'customer', ['batch_id'])
    
    # OrderLine table
    op.create_table(
        'order_line',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('customer_code', sa.String(255), nullable=False),
        sa.Column('product_key', sa.String(255), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('doc_ref', sa.String(255), nullable=False),
        sa.Column('doc_type', sa.String(50), nullable=True),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('amount_ht', sa.Float(), nullable=False),
        sa.Column('amount_ttc', sa.Float(), nullable=True),
        sa.Column('margin', sa.Float(), nullable=True),
        sa.Column('batch_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_code'], ['customer.customer_code']),
        sa.ForeignKeyConstraint(['product_key'], ['product.product_key']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_orderline_customer_code', 'order_line', ['customer_code'])
    op.create_index('ix_orderline_product_key', 'order_line', ['product_key'])
    op.create_index('ix_orderline_order_date', 'order_line', ['order_date'])
    op.create_index('ix_orderline_doc_ref', 'order_line', ['doc_ref'])
    op.create_index('ix_orderline_customer_date', 'order_line', ['customer_code', 'order_date'])
    
    # ContactEvent table
    op.create_table(
        'contact_event',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('customer_code', sa.String(255), nullable=False),
        sa.Column('contact_date', sa.Date(), nullable=False),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('campaign_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_code'], ['customer.customer_code']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_contact_customer_code', 'contact_event', ['customer_code'])
    op.create_index('ix_contact_contact_date', 'contact_event', ['contact_date'])
    op.create_index('ix_contact_campaign_id', 'contact_event', ['campaign_id'])
    op.create_index('ix_contact_customer_date', 'contact_event', ['customer_code', 'contact_date'])
    
    # ClientMasterProfile table
    op.create_table(
        'client_master_profile',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('customer_code', sa.String(255), nullable=False),
        sa.Column('premiere_date_achat', sa.Date(), nullable=True),
        sa.Column('derniere_date_achat', sa.Date(), nullable=True),
        sa.Column('recence_jours', sa.Integer(), nullable=True),
        sa.Column('nb_commandes', sa.Integer(), nullable=True),
        sa.Column('ca_ht', sa.Float(), nullable=True),
        sa.Column('r_score', sa.Integer(), nullable=True),
        sa.Column('f_score', sa.Integer(), nullable=True),
        sa.Column('m_score', sa.Integer(), nullable=True),
        sa.Column('rfm', sa.String(10), nullable=True),
        sa.Column('segment', sa.String(50), nullable=True),
        sa.Column('top_family_1', sa.String(255), nullable=True),
        sa.Column('top_family_1_ca_share', sa.Float(), nullable=True),
        sa.Column('top_family_2', sa.String(255), nullable=True),
        sa.Column('top_family_2_ca_share', sa.Float(), nullable=True),
        sa.Column('family_diversity_score', sa.Float(), nullable=True),
        sa.Column('top_grape_1', sa.String(255), nullable=True),
        sa.Column('top_grape_1_ca_share', sa.Float(), nullable=True),
        sa.Column('top_grape_2', sa.String(255), nullable=True),
        sa.Column('top_grape_2_ca_share', sa.Float(), nullable=True),
        sa.Column('top_sugar_1', sa.String(50), nullable=True),
        sa.Column('top_sugar_1_ca_share', sa.Float(), nullable=True),
        sa.Column('top_sugar_2', sa.String(50), nullable=True),
        sa.Column('top_sugar_2_ca_share', sa.Float(), nullable=True),
        sa.Column('top_budget_1', sa.String(50), nullable=True),
        sa.Column('top_budget_1_ca_share', sa.Float(), nullable=True),
        sa.Column('top_budget_2', sa.String(50), nullable=True),
        sa.Column('top_budget_2_ca_share', sa.Float(), nullable=True),
        sa.Column('aroma_axe_1', sa.String(50), nullable=True),
        sa.Column('aroma_score_1', sa.Float(), nullable=True),
        sa.Column('aroma_axe_2', sa.String(50), nullable=True),
        sa.Column('aroma_score_2', sa.Float(), nullable=True),
        sa.Column('aroma_axe_3', sa.String(50), nullable=True),
        sa.Column('aroma_score_3', sa.Float(), nullable=True),
        sa.Column('aroma_confidence', sa.Float(), nullable=True),
        sa.Column('aroma_level', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_code'], ['customer.customer_code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_code'),
    )
    op.create_index('ix_client_master_profile_customer_code', 'client_master_profile', ['customer_code'])
    op.create_index('ix_client_master_profile_segment', 'client_master_profile', ['segment'])
    
    # RecoRun table
    op.create_table(
        'reco_run',
        sa.Column('run_id', sa.String(255), nullable=False),
        sa.Column('config_hash', sa.String(64), nullable=False),
        sa.Column('code_version', sa.String(50), nullable=True),
        sa.Column('dataset_version', sa.String(50), nullable=True),
        sa.Column('run_timestamp', sa.DateTime(), nullable=False),
        sa.Column('total_customers', sa.Integer(), nullable=False),
        sa.Column('eligible_customers', sa.Integer(), nullable=False),
        sa.Column('exported_customers', sa.Integer(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('summary_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('run_id'),
    )
    op.create_index('ix_reco_run_timestamp', 'reco_run', ['run_timestamp'])
    
    # RecoItem table
    op.create_table(
        'reco_item',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('run_id', sa.String(255), nullable=False),
        sa.Column('customer_code', sa.String(255), nullable=False),
        sa.Column('scenario', sa.String(50), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('product_key', sa.String(255), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('explain_short', sa.String(512), nullable=True),
        sa.Column('reasons_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_code'], ['customer.customer_code']),
        sa.ForeignKeyConstraint(['product_key'], ['product.product_key']),
        sa.ForeignKeyConstraint(['run_id'], ['reco_run.run_id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reco_item_run_id', 'reco_item', ['run_id'])
    op.create_index('ix_reco_item_customer_code', 'reco_item', ['customer_code'])
    op.create_index('ix_reco_item_rank', 'reco_item', ['rank'])
    op.create_index('ix_reco_run_customer', 'reco_item', ['run_id', 'customer_code'])
    
    # AuditItem table
    op.create_table(
        'audit_item',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('run_id', sa.String(255), nullable=False),
        sa.Column('customer_code', sa.String(255), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('rule_code', sa.String(100), nullable=False),
        sa.Column('details_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['reco_run.run_id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_item_run_id', 'audit_item', ['run_id'])
    op.create_index('ix_audit_item_customer_code', 'audit_item', ['customer_code'])
    op.create_index('ix_audit_item_rule_code', 'audit_item', ['rule_code'])
    op.create_index('ix_audit_run_customer', 'audit_item', ['run_id', 'customer_code'])
    
    # OutcomeEvent table
    op.create_table(
        'outcome_event',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('customer_code', sa.String(255), nullable=False),
        sa.Column('campaign_id', sa.String(255), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('revenue_ht', sa.Float(), nullable=True),
        sa.Column('margin', sa.Float(), nullable=True),
        sa.Column('last_touch_reco_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_code'], ['customer.customer_code']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_outcome_event_customer_code', 'outcome_event', ['customer_code'])
    op.create_index('ix_outcome_event_campaign_id', 'outcome_event', ['campaign_id'])
    op.create_index('ix_outcome_event_purchase_date', 'outcome_event', ['purchase_date'])
    op.create_index('ix_outcome_customer_campaign', 'outcome_event', ['customer_code', 'campaign_id'])


def downgrade() -> None:
    """Drop initial schema."""
    op.drop_table('outcome_event')
    op.drop_table('audit_item')
    op.drop_table('reco_item')
    op.drop_table('reco_run')
    op.drop_table('client_master_profile')
    op.drop_table('contact_event')
    op.drop_table('order_line')
    op.drop_table('customer')
    op.drop_table('product_alias')
    op.drop_table('product')
