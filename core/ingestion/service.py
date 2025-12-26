"""Ingestion orchestration service."""

import logging
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from core.ingestion.schemas import FileType, IngestionReport, IngestionError
from core.ingestion.readers import CustomerReader, SalesLineReader, ContactReader
from core.ingestion.validators import (
    CustomerValidator, SalesLineValidator, ContactValidator,
    DependencyValidator
)
from core.ingestion.loaders import (
    RawDataLoader, IngestionErrorLoader, IngestionReportLoader
)

logger = logging.getLogger(__name__)


class IngestionService:
    """Service to orchestrate ingestion of CSV files."""

    def __init__(self, db: Session):
        """Initialize ingestion service.
        
        Args:
            db: SQLAlchemy session
        """
        self.db = db
        self.batch_id = str(uuid.uuid4())
        self.reports: Dict[str, IngestionReport] = {}

    def ingest_customers(
        self,
        file_path: Path,
    ) -> Tuple[IngestionReport, bool]:
        """Ingest customers from CSV file.
        
        Process:
            1. Read CSV file
            2. Normalize data
            3. Validate rows
            4. Load into raw_customers table
            5. Return report
        
        Args:
            file_path: Path to customers.csv
            
        Returns:
            Tuple of (report, success)
        """
        logger.info(f"Starting customer ingestion from {file_path}")
        
        # Step 1: Read
        rows, read_error = CustomerReader.read_and_normalize(file_path)
        if read_error:
            logger.error(f"Failed to read customers file: {read_error}")
            report = IngestionReport(
                batch_id=self.batch_id,
                file_type="customers",
                total_rows=0,
                valid_rows=0,
                error_rows=0,
                errors=[],
            )
            return report, False
        
        total_rows = len(rows)
        logger.info(f"Read {total_rows} customer rows")
        
        # Step 2: Validate
        valid_rows, validation_errors = CustomerValidator.validate_batch(rows)
        valid_count = len(valid_rows)
        error_count = len(validation_errors)
        
        logger.info(f"Validation: {valid_count} valid, {error_count} errors")
        
        # Step 3: Load
        loaded_count, load_errors = RawDataLoader.load_raw_customers(
            self.db, valid_rows, self.batch_id
        )
        
        # Load errors
        if validation_errors:
            error_dicts = [
                {
                    'row_number': e.row_number,
                    'file_type': e.file_type,
                    'error_code': e.error_code,
                    'error_message': e.error_message,
                    'raw_row': e.raw_row,
                }
                for e in validation_errors
            ]
            IngestionErrorLoader.load_errors(self.db, error_dicts, self.batch_id)
        
        # Load metadata
        IngestionReportLoader.load_batch_metadata(
            self.db, self.batch_id, "customers",
            total_rows, loaded_count, error_count
        )
        
        # Create report
        report = IngestionReport(
            batch_id=self.batch_id,
            file_type="customers",
            total_rows=total_rows,
            valid_rows=loaded_count,
            error_rows=error_count,
            errors=validation_errors,
        )
        
        self.reports["customers"] = report
        success = error_count == 0
        logger.info(f"Customer ingestion completed: {report.success_rate:.1f}% success")
        
        return report, success

    def ingest_sales_lines(
        self,
        file_path: Path,
        valid_customers: Optional[List[dict]] = None,
        product_aliases: Optional[Dict[str, str]] = None,
    ) -> Tuple[IngestionReport, bool]:
        """Ingest sales lines from CSV file.
        
        Process:
            1. Read CSV file
            2. Normalize data
            3. Validate rows
            4. Check customer exists (if valid_customers provided)
            5. Check product mapping (if product_aliases provided)
            6. Load into raw_sales_lines table
            7. Return report
        
        Args:
            file_path: Path to sales_lines.csv
            valid_customers: List of valid customer dicts (optional)
            product_aliases: Dict of {label_norm: product_key} (optional)
            
        Returns:
            Tuple of (report, success)
        """
        logger.info(f"Starting sales lines ingestion from {file_path}")
        
        # Step 1: Read
        rows, read_error = SalesLineReader.read_and_normalize(file_path)
        if read_error:
            logger.error(f"Failed to read sales lines file: {read_error}")
            report = IngestionReport(
                batch_id=self.batch_id,
                file_type="sales_lines",
                total_rows=0,
                valid_rows=0,
                error_rows=0,
                errors=[],
            )
            return report, False
        
        total_rows = len(rows)
        logger.info(f"Read {total_rows} sales line rows")
        
        # Step 2: Validate
        valid_rows, validation_errors = SalesLineValidator.validate_batch(rows)
        
        # Step 3: Check dependencies
        if valid_customers:
            customer_codes = {c.get('customer_code') for c in valid_customers}
            dependency_errors = []
            
            for row in valid_rows[:]:
                if row.get('customer_code') not in customer_codes:
                    error = IngestionError(
                        row_number=rows.index(next(
                            r for r in rows 
                            if r.get('customer_code') == row.get('customer_code')
                        )) + 2,
                        file_type="sales_lines",
                        error_code="CUSTOMER_NOT_FOUND",
                        error_message=f"Customer not found: {row.get('customer_code')}",
                        raw_row=row,
                    )
                    dependency_errors.append(error)
                    valid_rows.remove(row)
            
            validation_errors.extend(dependency_errors)
        
        # Step 4: Check product mappings
        if product_aliases:
            mapping_errors = []
            for row in valid_rows[:]:
                product_label_norm = row.get('product_label_norm')
                if product_label_norm not in product_aliases:
                    error = IngestionError(
                        row_number=rows.index(next(
                            r for r in rows 
                            if r.get('product_label') == row.get('product_label')
                        )) + 2,
                        file_type="sales_lines",
                        error_code="PRODUCT_NOT_FOUND",
                        error_message=f"Product not in alias mapping: {product_label_norm}",
                        raw_row=row,
                    )
                    mapping_errors.append(error)
                    valid_rows.remove(row)
            
            validation_errors.extend(mapping_errors)
        
        valid_count = len(valid_rows)
        error_count = len(validation_errors)
        
        logger.info(f"Validation: {valid_count} valid, {error_count} errors")
        
        # Step 5: Load
        loaded_count, load_errors = RawDataLoader.load_raw_sales_lines(
            self.db, valid_rows, self.batch_id
        )
        
        # Load errors
        if validation_errors:
            error_dicts = [
                {
                    'row_number': e.row_number,
                    'file_type': e.file_type,
                    'error_code': e.error_code,
                    'error_message': e.error_message,
                    'raw_row': e.raw_row,
                }
                for e in validation_errors
            ]
            IngestionErrorLoader.load_errors(self.db, error_dicts, self.batch_id)
        
        # Load metadata
        IngestionReportLoader.load_batch_metadata(
            self.db, self.batch_id, "sales_lines",
            total_rows, loaded_count, error_count
        )
        
        # Create report
        report = IngestionReport(
            batch_id=self.batch_id,
            file_type="sales_lines",
            total_rows=total_rows,
            valid_rows=loaded_count,
            error_rows=error_count,
            errors=validation_errors,
        )
        
        self.reports["sales_lines"] = report
        success = error_count == 0
        logger.info(f"Sales lines ingestion completed: {report.success_rate:.1f}% success")
        
        return report, success

    def ingest_contacts(
        self,
        file_path: Path,
        valid_customers: Optional[List[dict]] = None,
    ) -> Tuple[IngestionReport, bool]:
        """Ingest contact events from CSV file.
        
        Args:
            file_path: Path to contacts.csv
            valid_customers: List of valid customer dicts (optional)
            
        Returns:
            Tuple of (report, success)
        """
        logger.info(f"Starting contacts ingestion from {file_path}")
        
        # Step 1: Read
        rows, read_error = ContactReader.read_and_normalize(file_path)
        if read_error:
            logger.error(f"Failed to read contacts file: {read_error}")
            report = IngestionReport(
                batch_id=self.batch_id,
                file_type="contacts",
                total_rows=0,
                valid_rows=0,
                error_rows=0,
                errors=[],
            )
            return report, False
        
        total_rows = len(rows)
        logger.info(f"Read {total_rows} contact rows")
        
        # Step 2: Validate
        valid_rows, validation_errors = ContactValidator.validate_batch(rows)
        
        # Step 3: Check dependencies
        if valid_customers:
            customer_codes = {c.get('customer_code') for c in valid_customers}
            dependency_errors = []
            
            for row in valid_rows[:]:
                if row.get('customer_code') not in customer_codes:
                    error = IngestionError(
                        row_number=rows.index(next(
                            r for r in rows 
                            if r.get('customer_code') == row.get('customer_code')
                        )) + 2,
                        file_type="contacts",
                        error_code="CUSTOMER_NOT_FOUND",
                        error_message=f"Customer not found: {row.get('customer_code')}",
                        raw_row=row,
                    )
                    dependency_errors.append(error)
                    valid_rows.remove(row)
            
            validation_errors.extend(dependency_errors)
        
        valid_count = len(valid_rows)
        error_count = len(validation_errors)
        
        logger.info(f"Validation: {valid_count} valid, {error_count} errors")
        
        # Step 4: Load
        loaded_count, load_errors = RawDataLoader.load_raw_contacts(
            self.db, valid_rows, self.batch_id
        )
        
        # Load errors
        if validation_errors:
            error_dicts = [
                {
                    'row_number': e.row_number,
                    'file_type': e.file_type,
                    'error_code': e.error_code,
                    'error_message': e.error_message,
                    'raw_row': e.raw_row,
                }
                for e in validation_errors
            ]
            IngestionErrorLoader.load_errors(self.db, error_dicts, self.batch_id)
        
        # Load metadata
        IngestionReportLoader.load_batch_metadata(
            self.db, self.batch_id, "contacts",
            total_rows, loaded_count, error_count
        )
        
        # Create report
        report = IngestionReport(
            batch_id=self.batch_id,
            file_type="contacts",
            total_rows=total_rows,
            valid_rows=loaded_count,
            error_rows=error_count,
            errors=validation_errors,
        )
        
        self.reports["contacts"] = report
        success = error_count == 0
        logger.info(f"Contacts ingestion completed: {report.success_rate:.1f}% success")
        
        return report, success

    def get_batch_summary(self) -> Dict[str, IngestionReport]:
        """Get summary of all ingestion reports."""
        return self.reports
