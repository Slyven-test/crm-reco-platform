"""Ingestion module for CSV data import."""

from core.ingestion.schemas import (
    FileType,
    CustomerSchema,
    SalesLineSchema,
    ContactSchema,
    IngestionError,
    IngestionReport,
)
from core.ingestion.readers import (
    CSVReader,
    DataNormalizer,
    CustomerReader,
    SalesLineReader,
    ContactReader,
)
from core.ingestion.validators import (
    BaseValidator,
    CustomerValidator,
    SalesLineValidator,
    ContactValidator,
    DependencyValidator,
)
from core.ingestion.loaders import (
    RawDataLoader,
    IngestionErrorLoader,
    IngestionReportLoader,
)
from core.ingestion.service import IngestionService

__all__ = [
    'FileType',
    'CustomerSchema',
    'SalesLineSchema',
    'ContactSchema',
    'IngestionError',
    'IngestionReport',
    'CSVReader',
    'DataNormalizer',
    'CustomerReader',
    'SalesLineReader',
    'ContactReader',
    'BaseValidator',
    'CustomerValidator',
    'SalesLineValidator',
    'ContactValidator',
    'DependencyValidator',
    'RawDataLoader',
    'IngestionErrorLoader',
    'IngestionReportLoader',
    'IngestionService',
]
