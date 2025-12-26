"""Schema definitions and validation for CSV imports."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
import re


class FileType(str, Enum):
    """Supported CSV file types."""
    CUSTOMERS = "customers"
    SALES_LINES = "sales_lines"
    CONTACTS = "contacts"


class CustomerSchema(BaseModel):
    """Schema for customers.csv import."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    customer_code: str
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    @field_validator('customer_code')
    @classmethod
    def validate_customer_code(cls, v):
        """Validate customer code is not empty."""
        if not v or not v.strip():
            raise ValueError("customer_code is required")
        return v.strip()
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Normalize and validate email."""
        if v and v.strip():
            # Lowercase and remove spaces
            v = v.strip().lower()
            # Basic email validation
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
                raise ValueError(f"Invalid email format: {v}")
            return v
        return None
    
    @field_validator('postal_code')
    @classmethod
    def validate_postal_code(cls, v):
        """Validate postal code format."""
        if v and v.strip():
            v = v.strip()
            # Allow alphanumeric with hyphens
            if not re.match(r'^[a-zA-Z0-9\-]{2,20}$', v):
                raise ValueError(f"Invalid postal code: {v}")
            return v
        return None


class SalesLineSchema(BaseModel):
    """Schema for sales_lines.csv import."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    customer_code: str
    order_date: str  # Will be parsed to DATE
    doc_ref: str
    doc_type: Optional[str] = None
    product_label: str
    qty: str  # Will be parsed to FLOAT
    amount_ht: str  # Will be parsed to FLOAT
    amount_ttc: Optional[str] = None  # Will be parsed to FLOAT
    margin: Optional[str] = None  # Will be parsed to FLOAT

    @field_validator('customer_code')
    @classmethod
    def validate_customer_code(cls, v):
        """Validate customer code is not empty."""
        if not v or not v.strip():
            raise ValueError("customer_code is required")
        return v.strip()
    
    @field_validator('order_date')
    @classmethod
    def validate_order_date(cls, v):
        """Validate order date format (YYYY-MM-DD or DD/MM/YYYY)."""
        if not v or not v.strip():
            raise ValueError("order_date is required")
        v = v.strip()
        # Accept YYYY-MM-DD or DD/MM/YYYY or YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            return v
        elif re.match(r'^\d{2}/\d{2}/\d{4}$', v):
            # Will be converted to YYYY-MM-DD later
            return v
        else:
            raise ValueError(f"Invalid date format: {v} (use YYYY-MM-DD or DD/MM/YYYY)")
    
    @field_validator('doc_ref')
    @classmethod
    def validate_doc_ref(cls, v):
        """Validate document reference is not empty."""
        if not v or not v.strip():
            raise ValueError("doc_ref is required")
        return v.strip()
    
    @field_validator('product_label')
    @classmethod
    def validate_product_label(cls, v):
        """Validate product label is not empty."""
        if not v or not v.strip():
            raise ValueError("product_label is required")
        return v.strip()
    
    @field_validator('qty')
    @classmethod
    def validate_qty(cls, v):
        """Validate quantity is numeric and positive."""
        if not v or not v.strip():
            raise ValueError("qty is required")
        try:
            qty_float = float(v.replace(',', '.'))
            if qty_float <= 0:
                raise ValueError("qty must be positive")
            return str(qty_float)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid qty: {v} (must be numeric)")
    
    @field_validator('amount_ht')
    @classmethod
    def validate_amount_ht(cls, v):
        """Validate amount HT is numeric and non-negative."""
        if not v or not v.strip():
            raise ValueError("amount_ht is required")
        try:
            amount = float(v.replace(',', '.'))
            if amount < 0:
                raise ValueError("amount_ht must be non-negative")
            return str(amount)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid amount_ht: {v} (must be numeric)")
    
    @field_validator('amount_ttc')
    @classmethod
    def validate_amount_ttc(cls, v):
        """Validate amount TTC is numeric and non-negative."""
        if v and v.strip():
            try:
                amount = float(v.replace(',', '.'))
                if amount < 0:
                    raise ValueError("amount_ttc must be non-negative")
                return str(amount)
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid amount_ttc: {v} (must be numeric)")
        return None
    
    @field_validator('margin')
    @classmethod
    def validate_margin(cls, v):
        """Validate margin is numeric and non-negative."""
        if v and v.strip():
            try:
                margin = float(v.replace(',', '.'))
                if margin < 0:
                    raise ValueError("margin must be non-negative")
                return str(margin)
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid margin: {v} (must be numeric)")
        return None


class ContactSchema(BaseModel):
    """Schema for contacts.csv import (optional)."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    customer_code: str
    contact_date: str  # Will be parsed to DATE
    channel: Optional[str] = None
    status: Optional[str] = None
    campaign_id: Optional[str] = None

    @field_validator('customer_code')
    @classmethod
    def validate_customer_code(cls, v):
        """Validate customer code is not empty."""
        if not v or not v.strip():
            raise ValueError("customer_code is required")
        return v.strip()
    
    @field_validator('contact_date')
    @classmethod
    def validate_contact_date(cls, v):
        """Validate contact date format (YYYY-MM-DD or DD/MM/YYYY)."""
        if not v or not v.strip():
            raise ValueError("contact_date is required")
        v = v.strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            return v
        elif re.match(r'^\d{2}/\d{2}/\d{4}$', v):
            return v
        else:
            raise ValueError(f"Invalid date format: {v} (use YYYY-MM-DD or DD/MM/YYYY)")


class IngestionError(BaseModel):
    """Representation of an ingestion error."""
    row_number: int
    file_type: str
    error_code: str
    error_message: str
    raw_row: dict


class IngestionReport(BaseModel):
    """Report from ingestion batch."""
    batch_id: str
    file_type: str
    total_rows: int
    valid_rows: int
    error_rows: int
    errors: List[IngestionError]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_rows == 0:
            return 100.0
        return (self.valid_rows / self.total_rows) * 100
