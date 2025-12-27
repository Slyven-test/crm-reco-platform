"""
Étape 2: Transformation des VENTES_LIGNES
Version: 1.0
Auteur: CRM Ruhlmann

Ce script:
1. Charge les fichiers staging (ventes brutes)
2. Normalise les colonnes (client_code, dates, montants)
3. Crée les clés stables (Produit_Key, Document_ID)
4. Calcule Qty_Unit (conver conversion article → bouteilles)
5. Enregistre en curated/VENTES_LIGNES
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

from etl.config import STAGING_DIR, CURATED_DIR, logger
from etl.normalizers import (
    normalize_client_code,
    normalize_produit_label,
    normalize_date,
    normalize_float,
    normalize_email,
    normalize_string,
    create_document_id,
    calculate_qty_unit,
)

# ============================================================================
# CONSTANTES
# ============================================================================

COLUMNS_MAPPING = {
    # Colonnes de sortie souhaitées (ordre important)
    "client_code": "client_code",
    "date_livraison": "date_livraison",
    "document_id": "document_id",  # Créé dynamiquement
    "produit_key": "produit_key",  # Créé dynamiquement
    "produit_label": "produit_label",
    "article": "article",
    "qty_line": "qty_line",
    "qty_unit": "qty_unit",  # Créé dynamiquement
    "pu_ht": "pu_ht",
    "mt_ht": "mt_ht",
    "mt_ttc": "mt_ttc",
    "marge": "marge",
    "document_type": "document_type",
    "document_no": "document_no",
    "email": "email",
    "code_postal": "code_postal",
    "ville": "ville",
}

# ============================================================================
# FONCTION PRINCIPALE DE TRANSFORMATION
# ============================================================================

def transform_sales_data(input_file: Path) -> pd.DataFrame:
    """
    Transforme les données brutes de ventes.
    
    Args:
        input_file: Path vers le fichier staging (CSV/XLSX)
    
    Returns:
        DataFrame transformé
    """
    logger.info(f"Transform ventes: {input_file.name}")
    
    # Charger
    df = pd.read_csv(input_file, dtype=str, na_values=['', 'NA', 'NULL'])
    logger.info(f"  Chargé: {len(df)} lignes brutes")
    
    # Appliquer les transformations
    df = normalize_sales_columns(df)
    df = create_derived_columns(df)
    df = apply_business_rules(df)
    
    # Sélectionner et ordonner les colonnes de sortie
    output_cols = list(COLUMNS_MAPPING.keys())
    df = df[[col for col in output_cols if col in df.columns]]
    
    logger.info(f"  Transfé: {len(df)} lignes finales")
    return df


def normalize_sales_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise les colonnes brutes.
    """
    logger.info("  Normalisation des colonnes...")
    
    # client_code
    if "client_code" in df.columns:
        df["client_code"] = df["client_code"].apply(normalize_client_code)
    
    # date_livraison
    if "date_livraison" in df.columns:
        df["date_livraison"] = df["date_livraison"].apply(
            lambda x: normalize_date(x, format_input="%d/%m/%Y")  # Adapter si besoin
        )
    
    # produit_label
    if "produit_label" in df.columns:
        df["produit_label"] = df["produit_label"].apply(normalize_string)
    
    # Quantités
    if "qty_line" in df.columns:
        df["qty_line"] = df["qty_line"].apply(normalize_float)
    
    # Montants
    for col in ["pu_ht", "mt_ht", "mt_ttc", "marge"]:
        if col in df.columns:
            df[col] = df[col].apply(normalize_float)
    
    # Email
    if "email" in df.columns:
        df["email"] = df["email"].apply(normalize_email)
    
    # document_type, document_no
    if "document_type" in df.columns:
        df["document_type"] = df["document_type"].apply(
            lambda x: normalize_string(x).upper() if pd.notna(x) else None
        )
    
    logger.info("  ??? Colonnes normalisées")
    return df


def create_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crée les colonnes dérivées (Produit_Key, Document_ID, Qty_Unit).
    """
    logger.info("  Création des colonnes dérivées...")
    
    # Produit_Key (normalisé à partir du label)
    if "produit_label" in df.columns:
        df["produit_key"] = df["produit_label"].apply(normalize_produit_label)
    
    # Document_ID (clé unique du document)
    if "document_type" in df.columns and "document_no" in df.columns:
        df["document_id"] = df.apply(
            lambda row: create_document_id(
                row.get("document_type"),
                row.get("document_no"),
                row.get("date_livraison")
            ),
            axis=1
        )
    
    # Qty_Unit (conversion article → unités)
    if "qty_line" in df.columns:
        article_col = df.get("article", "UNKNOWN")
        df["qty_unit"] = df.apply(
            lambda row: calculate_qty_unit(
                row.get("qty_line"),
                row.get("article", "UNKNOWN")
            ),
            axis=1
        )
    
    logger.info("  ??? Colonnes dérivées créées")
    return df


def apply_business_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique les règles métier (filtres, exclusions, etc.).
    """
    logger.info("  Application des règles métier...")
    
    initial_count = len(df)
    
    # Régle 1: Exclure les lignes sans client_code
    df = df[df["client_code"].notna()]
    if len(df) < initial_count:
        logger.warning(f"    Exclu: {initial_count - len(df)} lignes sans client_code")
        initial_count = len(df)
    
    # Régle 2: Exclure les lignes sans montant (mt_ttc ou mt_ht)
    has_amount = (df["mt_ttc"].notna() | df["mt_ht"].notna())
    df = df[has_amount]
    if len(df) < initial_count:
        logger.warning(f"    Exclu: {initial_count - len(df)} lignes sans montant")
        initial_count = len(df)
    
    # Régle 3: Exclure les lignes avec qty = 0
    if "qty_unit" in df.columns:
        df = df[(df["qty_unit"] > 0) | (df["qty_unit"].isna())]
        if len(df) < initial_count:
            logger.warning(f"    Exclu: {initial_count - len(df)} lignes avec qty=0")
    
    logger.info(f"  ??? {len(df)} lignes conservées après règles")
    return df


# ============================================================================
# WORKFLOW D'INGESTION DES FICHIERS STAGING
# ============================================================================

def process_all_sales_files() -> dict:
    """
    Traite tous les fichiers staging de ventes.
    
    Returns:
        dict avec résultats
    """
    logger.info("\n=== TRANSFORMATION VENTES ===")
    
    # Détecter les fichiers de ventes en staging
    staging_files = [f for f in STAGING_DIR.glob("ventes_lignes_raw_*.csv")]
    logger.info(f"Détecté {len(staging_files)} fichier(s) de ventes en staging")
    
    results = {
        "files_processed": 0,
        "total_rows_input": 0,
        "total_rows_output": 0,
        "curated_files": [],
        "errors": [],
    }
    
    for staging_file in sorted(staging_files):
        try:
            df_transformed = transform_sales_data(staging_file)
            
            # Sauvegarder en curated
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            curated_file = CURATED_DIR / f"VENTES_LIGNES_curated_{timestamp}.csv"
            df_transformed.to_csv(curated_file, index=False, encoding="utf-8")
            
            logger.info(f"  ???  Sauvegardé en curated: {curated_file.name}")
            
            # Accumuler résultats
            results["files_processed"] += 1
            results["curated_files"].append(str(curated_file))
            
        except Exception as e:
            logger.error(f"  ??? Erreur transformant {staging_file.name}: {e}")
            results["errors"].append({"file": staging_file.name, "error": str(e)})
    
    logger.info(f"Transformation ventes: {results['files_processed']} fichiers traités")
    return results


if __name__ == "__main__":
    results = process_all_sales_files()
    print(f"\n??? Résultats transformation:")
    print(f"  Fichiers: {results['files_processed']}")
    print(f"  Fichiers curated: {results['curated_files']}")
    if results["errors"]:
        print(f"  Erreurs: {results['errors']}")
