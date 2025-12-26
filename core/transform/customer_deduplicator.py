"""Customer deduplication and master record creation."""

import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CustomerDeduplicator:
    """Deduplicate customer records and create master record."""

    def __init__(self, db: Session):
        """Initialize with database session.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db

    @staticmethod
    def get_email_groups(
        rows: List[Dict],
    ) -> Dict[str, List[Dict]]:
        """Group customer rows by email.
        
        Args:
            rows: List of customer rows from raw_customers
            
        Returns:
            Dict of {email: [rows]} for deduplication
        """
        groups = {}
        
        for row in rows:
            email = row.get('email')
            if email:
                if email not in groups:
                    groups[email] = []
                groups[email].append(row)
        
        return groups

    @staticmethod
    def get_phone_groups(
        rows: List[Dict],
    ) -> Dict[str, List[Dict]]:
        """Group customer rows by phone.
        
        Args:
            rows: List of customer rows from raw_customers
            
        Returns:
            Dict of {phone: [rows]} for deduplication
        """
        groups = {}
        
        for row in rows:
            phone = row.get('phone')
            if phone:
                if phone not in groups:
                    groups[phone] = []
                groups[phone].append(row)
        
        return groups

    @staticmethod
    def merge_customer_records(
        duplicates: List[Dict],
    ) -> Dict:
        """Merge duplicate customer records into master record.
        
        Strategy:
        1. Use first non-null value for each field (priority order)
        2. Customer codes: first occurrence
        3. Dates: keep first encountered
        
        Args:
            duplicates: List of duplicate customer dicts
            
        Returns:
            Merged customer dict
        """
        if not duplicates:
            return {}
        
        if len(duplicates) == 1:
            return duplicates[0]
        
        # Start with first record
        merged = dict(duplicates[0])
        
        # Track customer codes (comma-separated)
        customer_codes = [duplicates[0].get('customer_code')]
        
        # Merge remaining records
        for row in duplicates[1:]:
            for field, value in row.items():
                # Skip customer_code (will merge separately)
                if field == 'customer_code':
                    customer_codes.append(value)
                # Use first non-null value
                elif value and not merged.get(field):
                    merged[field] = value
        
        # Merge customer codes
        merged['customer_code'] = ','.join(filter(None, customer_codes))
        merged['customer_codes_merged'] = len(customer_codes) > 1
        merged['duplicate_count'] = len(duplicates)
        
        return merged

    def deduplicate_batch(
        self,
        batch_id: str,
    ) -> Tuple[List[Dict], Dict[str, List[str]]]:
        """Deduplicate customers from raw_customers batch.
        
        Args:
            batch_id: Batch ID to deduplicate
            
        Returns:
            Tuple of (dedup_customers, duplicates_map)
            - dedup_customers: List of deduplicated records
            - duplicates_map: Dict of {primary_id: [duplicate_ids]}
        """
        logger.info(f"Starting deduplication for batch {batch_id}")
        
        # Fetch raw customers for batch
        try:
            result = self.db.execute(text("""
                SELECT id, row_data
                FROM raw_customers
                WHERE batch_id = :batch_id
            """), {'batch_id': batch_id})
            
            rows_with_id = [
                {'_id': row[0], **row[1]} 
                for row in result
            ]
            
            logger.info(f"Fetched {len(rows_with_id)} raw customer rows")
            
        except Exception as e:
            logger.error(f"Failed to fetch raw customers: {str(e)}")
            return [], {}
        
        if not rows_with_id:
            return [], {}
        
        # Dedup by email
        email_groups = self.get_email_groups(rows_with_id)
        phone_groups = self.get_phone_groups(rows_with_id)
        
        dedup_customers = []
        duplicates_map = {}
        
        processed_ids: Set[int] = set()
        
        # Process email groups
        for email, group in email_groups.items():
            if len(group) > 1:
                # Multiple records with same email
                merged = self.merge_customer_records(group)
                primary_id = group[0]['_id']
                duplicate_ids = [str(r['_id']) for r in group[1:]]
                
                duplicates_map[primary_id] = duplicate_ids
                dedup_customers.append(merged)
                
                processed_ids.update(r['_id'] for r in group)
            elif len(group) == 1 and group[0]['_id'] not in processed_ids:
                # Single record, not yet processed
                dedup_customers.append(group[0])
                processed_ids.add(group[0]['_id'])
        
        # Add unprocessed records (no email)
        for row in rows_with_id:
            if row['_id'] not in processed_ids:
                dedup_customers.append(row)
                processed_ids.add(row['_id'])
        
        logger.info(
            f"Deduplication complete: {len(dedup_customers)} unique, "
            f"{len(duplicates_map)} duplicate groups"
        )
        
        return dedup_customers, duplicates_map
