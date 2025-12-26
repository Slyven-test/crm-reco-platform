"""CSV file readers and basic normalization."""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class CSVReader:
    """Generic CSV reader with UTF-8 encoding enforcement."""

    @staticmethod
    def read_csv(file_path: Path, encoding: str = 'utf-8') -> Tuple[List[Dict], Optional[Exception]]:
        """Read CSV file and return rows.
        
        Args:
            file_path: Path to CSV file
            encoding: File encoding (default utf-8)
            
        Returns:
            Tuple of (rows, error) where error is None if successful
        """
        try:
            rows = []
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                
                if not reader.fieldnames:
                    return [], ValueError(f"CSV file is empty or has no headers: {file_path}")
                
                for row_idx, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    rows.append(row)
            
            logger.info(f"Read {len(rows)} rows from {file_path.name}")
            return rows, None
            
        except UnicodeDecodeError as e:
            error = ValueError(f"File encoding error: {str(e)}. Ensure file is UTF-8 encoded.")
            logger.error(error)
            return [], error
        except FileNotFoundError as e:
            error = FileNotFoundError(f"File not found: {file_path}")
            logger.error(error)
            return [], error
        except Exception as e:
            error = Exception(f"Error reading CSV file: {str(e)}")
            logger.error(error)
            return [], error


class DataNormalizer:
    """Normalize and clean data from CSV."""

    @staticmethod
    def normalize_text(value: Optional[str]) -> Optional[str]:
        """Normalize text fields: trim, collapse spaces."""
        if not value:
            return None
        return ' '.join(value.strip().split())

    @staticmethod
    def normalize_email(value: Optional[str]) -> Optional[str]:
        """Normalize email: lowercase, trim spaces, remove around @."""
        if not value:
            return None
        # Remove spaces and lowercase
        email = value.strip().lower().replace(' ', '')
        # Remove spaces around @
        email = email.replace('@ ', '@').replace(' @', '@')
        return email if email else None

    @staticmethod
    def normalize_phone(value: Optional[str]) -> Optional[str]:
        """Normalize phone number: keep raw, also store normalized."""
        if not value:
            return None
        return value.strip()

    @staticmethod
    def normalize_date(value: Optional[str]) -> Optional[str]:
        """Convert date to ISO format (YYYY-MM-DD).
        
        Accepts: YYYY-MM-DD or DD/MM/YYYY
        Returns: YYYY-MM-DD
        """
        if not value:
            return None
        
        value = value.strip()
        
        # Already in YYYY-MM-DD format
        if len(value) == 10 and value[4] == '-':
            return value
        
        # DD/MM/YYYY format
        if len(value) == 10 and value[2] == '/':
            try:
                parts = value.split('/')
                day, month, year = parts[0], parts[1], parts[2]
                return f"{year}-{month}-{day}"
            except (IndexError, ValueError):
                return None
        
        return None

    @staticmethod
    def normalize_decimal(value: Optional[str]) -> Optional[float]:
        """Convert decimal string to float.
        
        Handles both comma and dot as decimal separator.
        """
        if not value or not value.strip():
            return None
        
        try:
            # Replace comma with dot for parsing
            numeric_value = float(value.strip().replace(',', '.'))
            return numeric_value
        except ValueError:
            return None

    @staticmethod
    def normalize_product_label(value: Optional[str]) -> Optional[str]:
        """Normalize product label for alias lookup.
        
        Lowercase, trim, collapse spaces.
        """
        if not value:
            return None
        # Lowercase and normalize spaces
        return DataNormalizer.normalize_text(value).lower()


class CustomerReader:
    """Reader specifically for customers.csv."""

    @staticmethod
    def read_and_normalize(file_path: Path) -> Tuple[List[Dict], Optional[Exception]]:
        """Read and normalize customer data."""
        rows, error = CSVReader.read_csv(file_path)
        if error:
            return [], error
        
        normalized_rows = []
        for row in rows:
            normalized_row = {
                'customer_code': row.get('customer_code', '').strip(),
                'last_name': DataNormalizer.normalize_text(row.get('last_name')),
                'first_name': DataNormalizer.normalize_text(row.get('first_name')),
                'email': DataNormalizer.normalize_email(row.get('email')),
                'phone': DataNormalizer.normalize_phone(row.get('phone')),
                'address': DataNormalizer.normalize_text(row.get('address')),
                'postal_code': row.get('postal_code', '').strip(),
                'city': DataNormalizer.normalize_text(row.get('city')),
                'country': DataNormalizer.normalize_text(row.get('country')),
            }
            normalized_rows.append(normalized_row)
        
        return normalized_rows, None


class SalesLineReader:
    """Reader specifically for sales_lines.csv."""

    @staticmethod
    def read_and_normalize(file_path: Path) -> Tuple[List[Dict], Optional[Exception]]:
        """Read and normalize sales line data."""
        rows, error = CSVReader.read_csv(file_path)
        if error:
            return [], error
        
        normalized_rows = []
        for row in rows:
            # Parse numeric and date fields
            order_date = DataNormalizer.normalize_date(row.get('order_date'))
            qty = DataNormalizer.normalize_decimal(row.get('qty'))
            amount_ht = DataNormalizer.normalize_decimal(row.get('amount_ht'))
            amount_ttc = DataNormalizer.normalize_decimal(row.get('amount_ttc'))
            margin = DataNormalizer.normalize_decimal(row.get('margin'))
            
            normalized_row = {
                'customer_code': row.get('customer_code', '').strip(),
                'order_date': order_date,
                'doc_ref': row.get('doc_ref', '').strip(),
                'doc_type': row.get('doc_type', '').strip() or None,
                'product_label': row.get('product_label', '').strip(),
                'product_label_norm': DataNormalizer.normalize_product_label(
                    row.get('product_label')
                ),
                'qty': qty,
                'amount_ht': amount_ht,
                'amount_ttc': amount_ttc,
                'margin': margin,
            }
            normalized_rows.append(normalized_row)
        
        return normalized_rows, None


class ContactReader:
    """Reader specifically for contacts.csv (optional)."""

    @staticmethod
    def read_and_normalize(file_path: Path) -> Tuple[List[Dict], Optional[Exception]]:
        """Read and normalize contact data."""
        rows, error = CSVReader.read_csv(file_path)
        if error:
            return [], error
        
        normalized_rows = []
        for row in rows:
            contact_date = DataNormalizer.normalize_date(row.get('contact_date'))
            
            normalized_row = {
                'customer_code': row.get('customer_code', '').strip(),
                'contact_date': contact_date,
                'channel': row.get('channel', '').strip() or None,
                'status': row.get('status', '').strip() or None,
                'campaign_id': row.get('campaign_id', '').strip() or None,
            }
            normalized_rows.append(normalized_row)
        
        return normalized_rows, None
