"""Row-level validation for ingestion data."""

import logging
from typing import List, Optional, Tuple
from pydantic import ValidationError
from core.ingestion.schemas import (
    CustomerSchema, SalesLineSchema, ContactSchema, IngestionError
)

logger = logging.getLogger(__name__)


class BaseValidator:
    """Base validator for row-level validation."""

    @staticmethod
    def validate_row(row: dict, schema_class, row_number: int) -> Tuple[Optional[dict], Optional[IngestionError]]:
        """Validate a single row against schema.
        
        Args:
            row: Raw row data
            schema_class: Pydantic schema class
            row_number: Row number for error reporting
            
        Returns:
            Tuple of (validated_row, error)
        """
        try:
            validated = schema_class(**row)
            return validated.model_dump(), None
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                error_messages.append(f"{field}: {msg}")
            
            ingestion_error = IngestionError(
                row_number=row_number,
                file_type="unknown",
                error_code="VALIDATION_ERROR",
                error_message=" | ".join(error_messages),
                raw_row=row,
            )
            return None, ingestion_error
        except Exception as e:
            ingestion_error = IngestionError(
                row_number=row_number,
                file_type="unknown",
                error_code="UNEXPECTED_ERROR",
                error_message=f"Unexpected error: {str(e)}",
                raw_row=row,
            )
            return None, ingestion_error


class CustomerValidator:
    """Validator for customer data."""

    @staticmethod
    def validate_batch(rows: List[dict]) -> Tuple[List[dict], List[IngestionError]]:
        """Validate batch of customer rows.
        
        Returns:
            Tuple of (valid_rows, errors)
        """
        valid_rows = []
        errors = []
        
        # Check for duplicates
        seen_codes = set()
        
        for row_idx, row in enumerate(rows, start=2):  # Start at 2 (header is row 1)
            # Check for duplicate customer codes
            customer_code = row.get('customer_code', '').strip()
            if customer_code in seen_codes:
                errors.append(IngestionError(
                    row_number=row_idx,
                    file_type="customers",
                    error_code="DUPLICATE_CUSTOMER",
                    error_message=f"Duplicate customer_code: {customer_code}",
                    raw_row=row,
                ))
                continue
            
            seen_codes.add(customer_code)
            
            # Validate against schema
            validated_row, error = BaseValidator.validate_row(
                row, CustomerSchema, row_idx
            )
            
            if error:
                error.file_type = "customers"
                errors.append(error)
            else:
                valid_rows.append(validated_row)
        
        return valid_rows, errors


class SalesLineValidator:
    """Validator for sales line data."""

    @staticmethod
    def validate_batch(rows: List[dict]) -> Tuple[List[dict], List[IngestionError]]:
        """Validate batch of sales line rows.
        
        Returns:
            Tuple of (valid_rows, errors)
        """
        valid_rows = []
        errors = []
        
        for row_idx, row in enumerate(rows, start=2):
            # Validate against schema
            validated_row, error = BaseValidator.validate_row(
                row, SalesLineSchema, row_idx
            )
            
            if error:
                error.file_type = "sales_lines"
                errors.append(error)
            else:
                # Check for missing product_label_norm (normalization failed)
                if not validated_row.get('product_label_norm'):
                    errors.append(IngestionError(
                        row_number=row_idx,
                        file_type="sales_lines",
                        error_code="INVALID_PRODUCT_LABEL",
                        error_message=f"Product label could not be normalized: {row.get('product_label')}",
                        raw_row=row,
                    ))
                else:
                    valid_rows.append(validated_row)
        
        return valid_rows, errors


class ContactValidator:
    """Validator for contact data."""

    @staticmethod
    def validate_batch(rows: List[dict]) -> Tuple[List[dict], List[IngestionError]]:
        """Validate batch of contact rows.
        
        Returns:
            Tuple of (valid_rows, errors)
        """
        valid_rows = []
        errors = []
        
        for row_idx, row in enumerate(rows, start=2):
            # Validate against schema
            validated_row, error = BaseValidator.validate_row(
                row, ContactSchema, row_idx
            )
            
            if error:
                error.file_type = "contacts"
                errors.append(error)
            else:
                valid_rows.append(validated_row)
        
        return valid_rows, errors


class DependencyValidator:
    """Cross-table dependency validation."""

    @staticmethod
    def check_customer_exists(
        customer_code: str, 
        valid_customers: dict, 
        context: str = "sales_line"
    ) -> Optional[str]:
        """Check if customer exists in valid customers.
        
        Args:
            customer_code: Customer code to check
            valid_customers: Dict of valid {customer_code: row}
            context: Context for error message
            
        Returns:
            Error message if not found, None if valid
        """
        if customer_code not in valid_customers:
            return f"Customer not found in customers batch: {customer_code} ({context})"
        return None

    @staticmethod
    def check_product_mapping(
        product_label_norm: str,
        product_aliases: dict,
        context: str = "sales_line"
    ) -> Optional[Tuple[str, str]]:
        """Check if product label maps to a product.
        
        Args:
            product_label_norm: Normalized product label
            product_aliases: Dict of {label_norm: product_key}
            context: Context for error message
            
        Returns:
            Tuple of (product_key, error) or (None, error_msg) if not found
        """
        if product_label_norm not in product_aliases:
            return None, f"Product not found in alias mapping: {product_label_norm} ({context})"
        return product_aliases[product_label_norm], None
