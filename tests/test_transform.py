"""Tests for transform module."""

import pytest
from core.transform.product_resolver import ProductResolver
from core.transform.customer_deduplicator import CustomerDeduplicator


class TestProductResolver:
    """Test product resolver."""
    
    def test_resolve_with_cache(self):
        """Test resolving product with in-memory cache."""
        # Note: requires database setup with ProductAlias table
        # Skipping for unit test without DB
        pass
    
    def test_resolve_not_found(self):
        """Test resolving non-existent product."""
        resolver = ProductResolver(db=None)  # Mock for test
        resolver._cache = {'pinot noir 2022': 'PINOT_NOIR_2022'}
        resolver._loaded = True
        
        product_key, error = resolver.resolve('unknown label', 'Unknown Label')
        assert product_key is None
        assert error is not None
        assert 'not found' in error.lower()


class TestCustomerDeduplicator:
    """Test customer deduplication."""
    
    def test_get_email_groups_empty(self):
        """Test email grouping with empty list."""
        rows = []
        groups = CustomerDeduplicator.get_email_groups(rows)
        assert groups == {}
    
    def test_get_email_groups_single(self):
        """Test email grouping with single email."""
        rows = [
            {'customer_code': 'C001', 'email': 'john@example.com'},
            {'customer_code': 'C002', 'email': 'john@example.com'},
        ]
        groups = CustomerDeduplicator.get_email_groups(rows)
        assert len(groups) == 1
        assert 'john@example.com' in groups
        assert len(groups['john@example.com']) == 2
    
    def test_get_email_groups_multiple(self):
        """Test email grouping with multiple emails."""
        rows = [
            {'customer_code': 'C001', 'email': 'john@example.com'},
            {'customer_code': 'C002', 'email': 'jane@example.com'},
            {'customer_code': 'C003', 'email': None},
        ]
        groups = CustomerDeduplicator.get_email_groups(rows)
        assert len(groups) == 2  # Only emails, no None
        assert 'john@example.com' in groups
        assert 'jane@example.com' in groups
    
    def test_merge_single_customer(self):
        """Test merging single customer (no duplicates)."""
        customer = {'customer_code': 'C001', 'first_name': 'John'}
        merged = CustomerDeduplicator.merge_customer_records([customer])
        
        assert merged['customer_code'] == 'C001'
        assert merged['first_name'] == 'John'
        assert merged['duplicate_count'] == 1
    
    def test_merge_duplicate_customers(self):
        """Test merging duplicate customers."""
        customers = [
            {'customer_code': 'C001', 'first_name': 'John', 'email': 'john@example.com', 'phone': None},
            {'customer_code': 'C002', 'first_name': None, 'email': 'john@example.com', 'phone': '+33612345678'},
        ]
        merged = CustomerDeduplicator.merge_customer_records(customers)
        
        assert 'C001' in merged['customer_code']  # Both codes merged
        assert 'C002' in merged['customer_code']
        assert merged['first_name'] == 'John'  # From first record
        assert merged['phone'] == '+33612345678'  # From second record
        assert merged['duplicate_count'] == 2
        assert merged['customers_codes_merged'] is True
    
    def test_merge_three_duplicates(self):
        """Test merging three duplicate customers."""
        customers = [
            {'customer_code': 'C001', 'first_name': 'John', 'last_name': None, 'email': 'john@example.com'},
            {'customer_code': 'C002', 'first_name': None, 'last_name': 'Doe', 'email': 'john@example.com'},
            {'customer_code': 'C003', 'first_name': None, 'last_name': None, 'email': 'john@example.com'},
        ]
        merged = CustomerDeduplicator.merge_customer_records(customers)
        
        assert merged['first_name'] == 'John'
        assert merged['last_name'] == 'Doe'
        assert merged['duplicate_count'] == 3
        # Check all codes are in merged customer_code
        codes_str = merged['customer_code']
        assert 'C001' in codes_str
        assert 'C002' in codes_str
        assert 'C003' in codes_str
    
    def test_get_phone_groups(self):
        """Test phone grouping."""
        rows = [
            {'customer_code': 'C001', 'phone': '+33612345678'},
            {'customer_code': 'C002', 'phone': '+33612345678'},
            {'customer_code': 'C003', 'phone': None},
        ]
        groups = CustomerDeduplicator.get_phone_groups(rows)
        
        assert len(groups) == 1  # Only phone groups, no None
        assert '+33612345678' in groups
        assert len(groups['+33612345678']) == 2


class TestCustomerDeduplicatorIntegration:
    """Integration tests for deduplicator (require DB)."""
    
    def test_deduplicate_batch(self, db_session):
        """Test deduplication of batch from raw_customers."""
        # This would require setting up test data in raw_customers table
        # Skipped for now as it requires full DB setup
        pass


class TestTransformPipelineStatus:
    """Test pipeline status tracking."""
    
    def test_status_to_dict(self):
        """Test converting status to dict."""
        from core.transform.orchestrator import TransformPipelineStatus
        from datetime import datetime, timedelta
        
        status = TransformPipelineStatus()
        status.customers_deduped = 100
        status.customers_loaded = 95
        status.order_lines_loaded = 500
        status.contact_events_loaded = 150
        status.master_profiles_created = 95
        
        status.start_time = datetime.utcnow()
        status.end_time = status.start_time + timedelta(seconds=5)
        
        status_dict = status.to_dict()
        
        assert status_dict['customers_deduped'] == 100
        assert status_dict['customers_loaded'] == 95
        assert status_dict['order_lines_loaded'] == 500
        assert status_dict['contact_events_loaded'] == 150
        assert status_dict['master_profiles_created'] == 95
        assert status_dict['duration_seconds'] > 4.9
        assert status_dict['duration_seconds'] < 5.1
    
    def test_status_duration_without_times(self):
        """Test duration calculation without start/end times."""
        from core.transform.orchestrator import TransformPipelineStatus
        
        status = TransformPipelineStatus()
        assert status.duration() is None
