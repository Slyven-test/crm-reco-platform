"""Load validated data into database raw tables."""

import json
import logging
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class IngestionBatch:
    """Represents a single ingestion batch."""

    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.created_at = datetime.utcnow()
        self.records_loaded = 0
        self.records_failed = 0

    def to_dict(self) -> dict:
        """Convert to dict representation."""
        return {
            'batch_id': self.batch_id,
            'created_at': self.created_at.isoformat(),
            'records_loaded': self.records_loaded,
            'records_failed': self.records_failed,
        }


def calculate_row_hash(row: dict) -> str:
    """Calculate hash of row for deduplication.
    
    Uses SHA256 of JSON representation.
    """
    row_json = json.dumps(row, sort_keys=True, default=str)
    return hashlib.sha256(row_json.encode()).hexdigest()


class RawDataLoader:
    """Load raw data into staging tables."""

    @staticmethod
    def load_raw_customers(
        db: Session,
        rows: List[dict],
        batch_id: str,
    ) -> Tuple[int, List[str]]:
        """Load customer rows into raw_customers staging table.
        
        Note: Creates raw_customers table if it doesn't exist.
        
        Returns:
            Tuple of (loaded_count, errors)
        """
        loaded_count = 0
        errors = []
        
        if not rows:
            return 0, []
        
        # Create raw_customers table if not exists
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS raw_customers (
                id BIGSERIAL PRIMARY KEY,
                batch_id VARCHAR(255) NOT NULL,
                row_hash VARCHAR(64) NOT NULL,
                row_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT now(),
                UNIQUE(batch_id, row_hash)
            )
        """))
        db.commit()
        
        for row in rows:
            try:
                row_hash = calculate_row_hash(row)
                
                # Try to insert
                db.execute(text("""
                    INSERT INTO raw_customers (batch_id, row_hash, row_data)
                    VALUES (:batch_id, :row_hash, :row_data)
                """), {
                    'batch_id': batch_id,
                    'row_hash': row_hash,
                    'row_data': json.dumps(row),
                })
                
                loaded_count += 1
                
            except Exception as e:
                errors.append(f"Row {loaded_count + 1}: {str(e)}")
                logger.warning(f"Failed to load customer row: {str(e)}")
        
        db.commit()
        logger.info(f"Loaded {loaded_count} customer rows from batch {batch_id}")
        return loaded_count, errors

    @staticmethod
    def load_raw_sales_lines(
        db: Session,
        rows: List[dict],
        batch_id: str,
    ) -> Tuple[int, List[str]]:
        """Load sales line rows into raw_sales_lines staging table.
        
        Returns:
            Tuple of (loaded_count, errors)
        """
        loaded_count = 0
        errors = []
        
        if not rows:
            return 0, []
        
        # Create raw_sales_lines table if not exists
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS raw_sales_lines (
                id BIGSERIAL PRIMARY KEY,
                batch_id VARCHAR(255) NOT NULL,
                row_hash VARCHAR(64) NOT NULL,
                row_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT now(),
                UNIQUE(batch_id, row_hash)
            )
        """))
        db.commit()
        
        for row in rows:
            try:
                row_hash = calculate_row_hash(row)
                
                db.execute(text("""
                    INSERT INTO raw_sales_lines (batch_id, row_hash, row_data)
                    VALUES (:batch_id, :row_hash, :row_data)
                """), {
                    'batch_id': batch_id,
                    'row_hash': row_hash,
                    'row_data': json.dumps(row),
                })
                
                loaded_count += 1
                
            except Exception as e:
                errors.append(f"Row {loaded_count + 1}: {str(e)}")
                logger.warning(f"Failed to load sales line: {str(e)}")
        
        db.commit()
        logger.info(f"Loaded {loaded_count} sales line rows from batch {batch_id}")
        return loaded_count, errors

    @staticmethod
    def load_raw_contacts(
        db: Session,
        rows: List[dict],
        batch_id: str,
    ) -> Tuple[int, List[str]]:
        """Load contact rows into raw_contacts staging table.
        
        Returns:
            Tuple of (loaded_count, errors)
        """
        loaded_count = 0
        errors = []
        
        if not rows:
            return 0, []
        
        # Create raw_contacts table if not exists
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS raw_contacts (
                id BIGSERIAL PRIMARY KEY,
                batch_id VARCHAR(255) NOT NULL,
                row_hash VARCHAR(64) NOT NULL,
                row_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT now(),
                UNIQUE(batch_id, row_hash)
            )
        """))
        db.commit()
        
        for row in rows:
            try:
                row_hash = calculate_row_hash(row)
                
                db.execute(text("""
                    INSERT INTO raw_contacts (batch_id, row_hash, row_data)
                    VALUES (:batch_id, :row_hash, :row_data)
                """), {
                    'batch_id': batch_id,
                    'row_hash': row_hash,
                    'row_data': json.dumps(row),
                })
                
                loaded_count += 1
                
            except Exception as e:
                errors.append(f"Row {loaded_count + 1}: {str(e)}")
                logger.warning(f"Failed to load contact: {str(e)}")
        
        db.commit()
        logger.info(f"Loaded {loaded_count} contact rows from batch {batch_id}")
        return loaded_count, errors


class IngestionErrorLoader:
    """Load ingestion errors into database."""

    @staticmethod
    def load_errors(
        db: Session,
        errors: List[dict],
        batch_id: str,
    ) -> int:
        """Load validation errors into ingestion_errors table.
        
        Returns:
            Number of errors loaded
        """
        if not errors:
            return 0
        
        # Create table if not exists
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ingestion_errors (
                id BIGSERIAL PRIMARY KEY,
                batch_id VARCHAR(255) NOT NULL,
                file_name VARCHAR(255),
                row_number INTEGER NOT NULL,
                error_code VARCHAR(100) NOT NULL,
                error_message TEXT NOT NULL,
                raw_row JSONB,
                created_at TIMESTAMP DEFAULT now(),
                INDEX idx_batch_id (batch_id)
            )
        """))
        db.commit()
        
        loaded_count = 0
        for error in errors:
            try:
                db.execute(text("""
                    INSERT INTO ingestion_errors 
                    (batch_id, file_name, row_number, error_code, error_message, raw_row)
                    VALUES (:batch_id, :file_name, :row_number, :error_code, :error_message, :raw_row)
                """), {
                    'batch_id': batch_id,
                    'file_name': error.get('file_type'),
                    'row_number': error.get('row_number'),
                    'error_code': error.get('error_code'),
                    'error_message': error.get('error_message'),
                    'raw_row': json.dumps(error.get('raw_row', {})),
                })
                loaded_count += 1
            except Exception as e:
                logger.warning(f"Failed to load error: {str(e)}")
        
        db.commit()
        logger.info(f"Loaded {loaded_count} errors from batch {batch_id}")
        return loaded_count


class IngestionReportLoader:
    """Load ingestion report metadata."""

    @staticmethod
    def load_batch_metadata(
        db: Session,
        batch_id: str,
        file_type: str,
        total_rows: int,
        valid_rows: int,
        error_count: int,
    ) -> None:
        """Load batch ingestion metadata.
        
        Creates ingestion_batches table if needed.
        """
        # Create table if not exists
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS ingestion_batches (
                id BIGSERIAL PRIMARY KEY,
                batch_id VARCHAR(255) NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                total_rows INTEGER NOT NULL,
                valid_rows INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT now(),
                UNIQUE(batch_id, file_type)
            )
        """))
        db.commit()
        
        try:
            db.execute(text("""
                INSERT INTO ingestion_batches 
                (batch_id, file_type, total_rows, valid_rows, error_count)
                VALUES (:batch_id, :file_type, :total_rows, :valid_rows, :error_count)
            """), {
                'batch_id': batch_id,
                'file_type': file_type,
                'total_rows': total_rows,
                'valid_rows': valid_rows,
                'error_count': error_count,
            })
            db.commit()
            logger.info(f"Loaded batch metadata for {batch_id}/{file_type}")
        except Exception as e:
            logger.warning(f"Failed to load batch metadata: {str(e)}")
