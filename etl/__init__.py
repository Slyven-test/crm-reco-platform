"""
Package ETL pour le pipeline iSaVigne → CRM
Version: 1.0
Auteur: Projet CRM Ruhlmann

Modules:
  - config: Configuration centralisée
  - normalizers: Fonctions de normalisation des données
  - ingest_raw: Étape 1 - Détection et copie des fichiers RAW
  - transform_sales: Étape 2 - Transformation des données
  - load_postgres: Étape 3 - Chargement en base (coming soon)

Usage:
  from etl.config import logger
  from etl.ingest_raw import ingest_all_datasets
  
  results = ingest_all_datasets()
  logger.info(f"Pipeline terminé: {results}")
"""

__version__ = "1.0.0"
__author__ = "Projet CRM Ruhlmann"

from etl.config import (
    logger,
    RAW_DIR,
    STAGING_DIR,
    CURATED_DIR,
    LOGS_DIR,
    DATABASE_URL,
)

__all__ = [
    "logger",
    "RAW_DIR",
    "STAGING_DIR",
    "CURATED_DIR",
    "LOGS_DIR",
    "DATABASE_URL",
]
