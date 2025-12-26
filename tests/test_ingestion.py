"""Tests for ingestion module."""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
import csv

from core.ingestion.schemas import (
    CustomerSchema, SalesLineSchema, ContactSchema,
    IngestionError, IngestionReport
)
from core.ingestion.readers import (
    CSVReader, DataNormalizer, CustomerReader, 
    SalesLineReader, ContactReader
)
from core.ingestion.validators import (
    CustomerValidator, SalesLineValidator, ContactValidator
)


class TestDataNormalizer:
    """Test data normalization functions."""
    
    def test_normalize_text(self):
        """Test text normalization."""
        assert DataNormalizer.normalize_text("  hello   world  ") == "hello world"
        assert DataNormalizer.normalize_text(None) is None
        assert DataNormalizer.normalize_text("") is None
    
    def test_normalize_email(self):
        """Test email normalization."""
        assert DataNormalizer.normalize_email("  Test@Example.COM  ") == "test@example.com"
        assert DataNormalizer.normalize_email("test @ example.com") == "test@example.com"
        assert DataNormalizer.normalize_email(None) is None
    
    def test_normalize_date(self):
        """Test date normalization."""
        assert DataNormalizer.normalize_date("2024-01-15") == "2024-01-15"
        assert DataNormalizer.normalize_date("15/01/2024") == "2024-01-15"
        assert DataNormalizer.normalize_date(None) is None
        assert DataNormalizer.normalize_date("invalid") is None
    
    def test_normalize_decimal(self):
        """Test decimal normalization."""
        assert DataNormalizer.normalize_decimal("123.45") == 123.45
        assert DataNormalizer.normalize_decimal("123,45") == 123.45
        assert DataNormalizer.normalize_decimal("  100  ") == 100.0
        assert DataNormalizer.normalize_decimal(None) is None
        assert DataNormalizer.normalize_decimal("invalid") is None
    
    def test_normalize_product_label(self):
        """Test product label normalization."""
        assert DataNormalizer.normalize_product_label("  PINOT NOIR 2022  ") == "pinot noir 2022"
        assert DataNormalizer.normalize_product_label("Château  Margaux") == "château margaux"
        assert DataNormalizer.normalize_product_label(None) is None


class TestCSVReader:
    """Test CSV reading functionality."""
    
    def test_read_valid_csv(self):
        """Test reading valid CSV file."""
        # Create temporary CSV
        with NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'email'])
            writer.writeheader()
            writer.writerow({'name': 'John Doe', 'email': 'john@example.com'})
            writer.writerow({'name': 'Jane Doe', 'email': 'jane@example.com'})
            f.flush()
            
            rows, error = CSVReader.read_csv(Path(f.name))
            
            assert error is None
            assert len(rows) == 2
            assert rows[0]['name'] == 'John Doe'
            assert rows[1]['name'] == 'Jane Doe'
    
    def test_read_nonexistent_file(self):
        """Test reading non-existent file."""
        rows, error = CSVReader.read_csv(Path('/nonexistent/file.csv'))
        
        assert rows == []
        assert error is not None
        assert isinstance(error, FileNotFoundError)


class TestCustomerSchema:
    """Test customer schema validation."""
    
    def test_valid_customer(self):
        """Test valid customer data."""
        data = {
            'customer_code': 'CUST001',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'postal_code': '75001',
        }
        customer = CustomerSchema(**data)
        assert customer.customer_code == 'CUST001'
        assert customer.email == 'john@example.com'
    
    def test_missing_customer_code(self):
        """Test missing required customer_code."""
        data = {
            'first_name': 'John',
            'email': 'john@example.com',
        }
        with pytest.raises(Exception):
            CustomerSchema(**data)
    
    def test_invalid_email(self):
        """Test invalid email format."""
        data = {
            'customer_code': 'CUST001',
            'email': 'not-an-email',
        }
        with pytest.raises(Exception):
            CustomerSchema(**data)
    
    def test_invalid_postal_code(self):
        """Test invalid postal code format."""
        data = {
            'customer_code': 'CUST001',
            'postal_code': '12345678901234567890123',  # Too long
        }
        with pytest.raises(Exception):
            CustomerSchema(**data)


class TestSalesLineSchema:
    """Test sales line schema validation."""
    
    def test_valid_sales_line(self):
        """Test valid sales line data."""
        data = {
            'customer_code': 'CUST001',
            'order_date': '2024-01-15',
            'doc_ref': 'INV001',
            'product_label': 'Pinot Noir 2022',
            'qty': '5',
            'amount_ht': '250.50',
        }
        line = SalesLineSchema(**data)
        assert line.customer_code == 'CUST001'
        assert line.order_date == '2024-01-15'
    
    def test_invalid_quantity(self):
        """Test invalid quantity (negative)."""
        data = {
            'customer_code': 'CUST001',
            'order_date': '2024-01-15',
            'doc_ref': 'INV001',
            'product_label': 'Pinot Noir 2022',
            'qty': '-5',
            'amount_ht': '250.50',
        }
        with pytest.raises(Exception):
            SalesLineSchema(**data)
    
    def test_invalid_date_format(self):
        """Test invalid date format."""
        data = {
            'customer_code': 'CUST001',
            'order_date': '15-01-2024',  # Wrong format
            'doc_ref': 'INV001',
            'product_label': 'Pinot Noir 2022',
            'qty': '5',
            'amount_ht': '250.50',
        }
        with pytest.raises(Exception):
            SalesLineSchema(**data)


class TestCustomerValidator:
    """Test customer batch validation."""
    
    def test_valid_batch(self):
        """Test batch with valid customers."""
        rows = [
            {
                'customer_code': 'CUST001',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'phone': None,
                'address': None,
                'postal_code': '75001',
                'city': 'Paris',
                'country': None,
            },
            {
                'customer_code': 'CUST002',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane@example.com',
                'phone': None,
                'address': None,
                'postal_code': '75002',
                'city': 'Paris',
                'country': None,
            },
        ]
        valid, errors = CustomerValidator.validate_batch(rows)
        assert len(valid) == 2
        assert len(errors) == 0
    
    def test_duplicate_customers(self):
        """Test batch with duplicate customer codes."""
        rows = [
            {
                'customer_code': 'CUST001',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'phone': None,
                'address': None,
                'postal_code': '75001',
                'city': 'Paris',
                'country': None,
            },
            {
                'customer_code': 'CUST001',  # Duplicate!
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane@example.com',
                'phone': None,
                'address': None,
                'postal_code': '75002',
                'city': 'Paris',
                'country': None,
            },
        ]
        valid, errors = CustomerValidator.validate_batch(rows)
        assert len(valid) == 1  # Only first one is valid
        assert len(errors) == 1  # Second one is duplicate
        assert errors[0].error_code == 'DUPLICATE_CUSTOMER'


class TestSalesLineValidator:
    """Test sales line batch validation."""
    
    def test_valid_batch(self):
        """Test batch with valid sales lines."""
        rows = [
            {
                'customer_code': 'CUST001',
                'order_date': '2024-01-15',
                'doc_ref': 'INV001',
                'doc_type': None,
                'product_label': 'Pinot Noir 2022',
                'qty': '5',
                'amount_ht': '250.50',
                'amount_ttc': None,
                'margin': None,
            },
        ]
        valid, errors = SalesLineValidator.validate_batch(rows)
        assert len(valid) == 1
        assert len(errors) == 0


class TestIngestionReport:
    """Test ingestion report."""
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        report = IngestionReport(
            batch_id="test-batch",
            file_type="customers",
            total_rows=10,
            valid_rows=8,
            error_rows=2,
            errors=[],
        )
        assert report.success_rate == 80.0
    
    def test_success_rate_zero_rows(self):
        """Test success rate with zero total rows."""
        report = IngestionReport(
            batch_id="test-batch",
            file_type="customers",
            total_rows=0,
            valid_rows=0,
            error_rows=0,
            errors=[],
        )
        assert report.success_rate == 100.0
