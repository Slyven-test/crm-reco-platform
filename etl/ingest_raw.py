"""
Étape 1: Détection et copie des fichiers RAW
Version: 1.0
Auteur: CRM Ruhlmann

Ce script:
1. Détecte les nouveaux fichiers dans exports\\raw\\isavigne
2. Valide leur format (CSV/XLSX)
3. Copie en staging avec horodatage
4. Met à jour un manifest (traçabilité)
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

from etl.config import (
    RAW_DIR, STAGING_DIR, CONFIG_DIR,
    VENTES_SCHEMA, CLIENTS_SCHEMA, PRODUITS_SCHEMA,
    logger
)

# ============================================================================
# CONSTANTES
# ============================================================================

SUPPORTED_FORMATS = {".csv", ".xlsx", ".xls"}
MANIFEST_FILE = CONFIG_DIR / "manifest_raw.json"

# Mapping: sous-dossier RAW → schéma attendu
DATASET_SCHEMAS = {
    "ventes_lignes": VENTES_SCHEMA,
    "clients": CLIENTS_SCHEMA,
    "produits": PRODUITS_SCHEMA,
}

# ============================================================================
# DÉTECTION DES FICHIERS
# ============================================================================

def detect_raw_files(dataset_type: str) -> list:
    """
    Détecte les fichiers RAW non encore traités.
    
    Args:
        dataset_type: 'ventes_lignes', 'clients', etc.
    
    Returns:
        List[Path] des fichiers à traiter
    """
    dataset_dir = RAW_DIR / dataset_type
    
    if not dataset_dir.exists():
        logger.warning(f"Dossier RAW {dataset_dir} n'existe pas")
        return []
    
    files = []
    for file in sorted(dataset_dir.iterdir()):
        if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS:
            files.append(file)
    
    logger.info(f"Détecté {len(files)} fichier(s) dans {dataset_type}")
    return files


def load_manifest() -> dict:
    """
    Charge le manifest (fichiers déjà traités).
    """
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"processed_files": {}}


def save_manifest(manifest: dict):
    """
    Sauvegarde le manifest.
    """
    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def is_file_processed(filepath: Path, manifest: dict) -> bool:
    """
    Vérifie si un fichier a déjà été traité.
    Basé sur le nom complet du fichier.
    """
    return str(filepath) in manifest.get("processed_files", {})


# ============================================================================
# VALIDATION & CHARGEMENT
# ============================================================================

def read_raw_file(filepath: Path) -> pd.DataFrame:
    """
    Lit un fichier RAW (CSV ou XLSX).
    """
    try:
        if filepath.suffix.lower() == ".csv":
            df = pd.read_csv(filepath, dtype=str, na_values=['', 'NA', 'NULL'])
        elif filepath.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(filepath, sheet_name=0, dtype=str, na_values=['', 'NA', 'NULL'])
        else:
            raise ValueError(f"Format non supporté: {filepath.suffix}")
        
        logger.info(f"Chargé {len(df)} lignes depuis {filepath.name}")
        return df
    
    except Exception as e:
        logger.error(f"Erreur en lisant {filepath}: {e}")
        raise


def validate_schema(df: pd.DataFrame, expected_schema: dict, dataset_type: str) -> bool:
    """
    Vérifie que le DataFrame contient au moins les colonnes essentielles.
    
    Args:
        df: DataFrame à valider
        expected_schema: dict {column: type}
        dataset_type: pour les logs
    
    Returns:
        True si valide, False sinon
    """
    actual_cols = set(df.columns)
    expected_cols = set(expected_schema.keys())
    
    # Vérifier que toutes les colonnes attendues sont présentes
    missing = expected_cols - actual_cols
    if missing:
        logger.error(
            f"Colonnes manquantes dans {dataset_type}: {missing}\n"
            f"Colonnes trouvées: {actual_cols}"
        )
        return False
    
    logger.info(f"Schéma validé pour {dataset_type}")
    return True


def check_data_quality(df: pd.DataFrame, dataset_type: str) -> dict:
    """
    Vérifie la qualité basique des données.
    
    Returns:
        dict avec statistiques (nb_rows, null_counts, etc.)
    """
    stats = {
        "nb_rows": len(df),
        "nb_cols": len(df.columns),
        "null_counts": df.isnull().sum().to_dict(),
        "duplicates": df.duplicated().sum(),
    }
    
    logger.info(f"QA {dataset_type}: {stats['nb_rows']} lignes, {stats['duplicates']} doublons")
    
    # Avertissement si beaucoup de nulls
    for col, null_count in stats["null_counts"].items():
        if null_count > 0:
            pct = (null_count / len(df)) * 100
            if pct > 50:
                logger.warning(f"  {col}: {null_count} nulls ({pct:.1f}%)")
    
    return stats


# ============================================================================
# COPIE EN STAGING
# ============================================================================

def copy_to_staging(raw_filepath: Path, dataset_type: str) -> Path:
    """
    Copie un fichier RAW en staging avec horodatage.
    
    RAW: exports\\raw\\isavigne\\ventes_lignes\\ventes_lignes_2025-12-27.csv
    → STAGING: exports\\staging\\ventes_lignes_raw_20251227_120000.csv
    
    Returns:
        Path du fichier en staging
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    staging_name = f"{dataset_type}_raw_{timestamp}{raw_filepath.suffix}"
    staging_path = STAGING_DIR / staging_name
    
    shutil.copy2(raw_filepath, staging_path)
    logger.info(f"Copié en staging: {staging_path.name}")
    
    return staging_path


# ============================================================================
# WORKFLOW PRINCIPAL
# ============================================================================

def ingest_dataset(dataset_type: str) -> dict:
    """
    Traite un type de dataset complet.
    
    Args:
        dataset_type: 'ventes_lignes', 'clients', etc.
    
    Returns:
        dict avec résultats (nb_processed, errors, etc.)
    """
    logger.info(f"\n=== INGESTION {dataset_type.upper()} ===")
    
    manifest = load_manifest()
    expected_schema = DATASET_SCHEMAS.get(dataset_type, {})
    
    results = {
        "dataset_type": dataset_type,
        "files_processed": 0,
        "files_skipped": 0,
        "total_rows": 0,
        "errors": [],
        "staging_files": [],
    }
    
    # Détecter les fichiers RAW
    raw_files = detect_raw_files(dataset_type)
    if not raw_files:
        logger.warning(f"Aucun fichier détecté pour {dataset_type}")
        return results
    
    # Traiter chaque fichier
    for raw_filepath in raw_files:
        logger.info(f"\nTraité: {raw_filepath.name}")
        
        # Vérifier si déjà traité
        if is_file_processed(raw_filepath, manifest):
            logger.info(f"  → Déjà traité, ignoré")
            results["files_skipped"] += 1
            continue
        
        try:
            # Charger
            df = read_raw_file(raw_filepath)
            
            # Valider schéma
            if expected_schema and not validate_schema(df, expected_schema, dataset_type):
                raise ValueError(f"Schéma invalide pour {raw_filepath.name}")
            
            # Vérifier qualité
            qa_stats = check_data_quality(df, dataset_type)
            
            # Copier en staging
            staging_path = copy_to_staging(raw_filepath, dataset_type)
            
            # Mettre à jour manifest
            manifest["processed_files"][str(raw_filepath)] = {
                "processed_at": datetime.now().isoformat(),
                "staging_path": str(staging_path),
                "nb_rows": len(df),
                "qa_stats": qa_stats,
            }
            
            # Accumuler résultats
            results["files_processed"] += 1
            results["total_rows"] += len(df)
            results["staging_files"].append(str(staging_path))
            
            logger.info(f"  ✅ Succès: {len(df)} lignes en staging")
        
        except Exception as e:
            logger.error(f"  ❌ Erreur: {e}")
            results["errors"].append({"file": raw_filepath.name, "error": str(e)})
    
    # Sauvegarder manifest
    save_manifest(manifest)
    
    # Résumé
    logger.info(f"\n{dataset_type}: {results['files_processed']} fichiers traités, {results['total_rows']} lignes au total")
    
    return results


def ingest_all_datasets() -> dict:
    """
    Lance l'ingestion pour tous les types de datasets.
    """
    logger.info("\n" + "="*60)
    logger.info("DÉBUT INGESTION RAW")
    logger.info("="*60)
    
    all_results = {}
    
    for dataset_type in DATASET_SCHEMAS.keys():
        results = ingest_dataset(dataset_type)
        all_results[dataset_type] = results
    
    logger.info("\n" + "="*60)
    logger.info("FIN INGESTION RAW")
    logger.info("="*60)
    
    return all_results


if __name__ == "__main__":
    results = ingest_all_datasets()
    
    # Afficher résumé final
    print("\n✅ RéSUMÉ INGESTION:")
    for dataset_type, r in results.items():
        print(f"  {dataset_type}: {r['files_processed']} fichiers, {r['total_rows']} lignes")
        if r["errors"]:
            print(f"    Erreurs: {r['errors']}")
