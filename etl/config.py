"""
Configuration centrale pour le pipeline ETL iSaVigne
Version: 1.0
Auteur: CRM Ruhlmann
"""

import os
from pathlib import Path
from datetime import datetime
import logging

# ============================================================================
# CHEMINS DE BASE
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
ETL_ROOT = PROJECT_ROOT / "etl"

# Arborescence exports
EXPORTS_ROOT = Path("C:\\Users\\Valentin\\Desktop\\CRM_Ruhlmann\\exports")
RAW_DIR = EXPORTS_ROOT / "raw" / "isavigne"
STAGING_DIR = EXPORTS_ROOT / "staging"
CURATED_DIR = EXPORTS_ROOT / "curated"
LOGS_DIR = EXPORTS_ROOT / "logs"
CONFIG_DIR = EXPORTS_ROOT / "config"

# Créer les dossiers s'ils n'existent pas
for directory in [RAW_DIR, STAGING_DIR, CURATED_DIR, LOGS_DIR, CONFIG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    # Créer les sous-dossiers de RAW
    if "raw" in str(directory):
        for subdir in ["ventes_lignes", "clients", "produits", "stock", "contacts"]:
            (directory / subdir).mkdir(parents=True, exist_ok=True)

# ============================================================================
# BASE DE DONNÉES
# ============================================================================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "crm_reco")
DB_USER = os.getenv("DB_USER", "crm_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "secure_password_change_me")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================================
# SCHÉMA DE DONNÉES
# ============================================================================

# Schéma attendu pour VENTES_LIGNES
VENTES_SCHEMA = {
    "client_code": "str",
    "date_livraison": "datetime",
    "produit_label": "str",
    "qty_line": "float",
    "pu_ht": "float",
    "mt_ht": "float",
    "mt_ttc": "float",
    "marge": "float",
    "document_type": "str",
    "document_no": "str",
    "order_detail_no": "str",
    "email": "str",
    "code_postal": "str",
    "ville": "str",
    "article": "str",
}

# Schéma attendu pour CLIENTS
CLIENTS_SCHEMA = {
    "client_code": "str",
    "nom": "str",
    "prenom": "str",
    "email": "str",
    "telephone": "str",
    "adresse": "str",
    "code_postal": "str",
    "ville": "str",
    "pays": "str",
}

# Schéma attendu pour PRODUITS
PRODUITS_SCHEMA = {
    "produit": "str",
    "article": "str",
    "millesime": "str",
    "famille_crm": "str",
    "sous_famille": "str",
    "macro_categorie": "str",
    "prix_ttc": "float",
    "price_band": "str",
    "premium_tier": "str",
}

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configure les logs pour le pipeline ETL."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_file = LOGS_DIR / f"run_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# STATE & TRAÇABILITÉ
# ============================================================================

STATE_FILE = CONFIG_DIR / "state.json"

# État par défaut
DEFAULT_STATE = {
    "last_sync_ventes": "2020-01-01",
    "last_sync_clients": "2020-01-01",
    "last_sync_produits": "2020-01-01",
    "last_sync_stock": "2020-01-01",
    "last_run_date": None,
    "last_run_success": False,
}

# ============================================================================
# RÈGLES DE QUALITÉ
# ============================================================================

# Fréquence minimale de contact (jours)
MIN_DAYS_BETWEEN_CONTACTS = 135

# Exclusion rebuy (jours)
MIN_DAYS_BEFORE_REBUY = 60

# Nombre de recommandations par run
NB_RECOMMENDATIONS = 3

if __name__ == "__main__":
    print(f"✅ Configuration chargée")
    print(f"   Raw dir: {RAW_DIR}")
    print(f"   Curated dir: {CURATED_DIR}")
    print(f"   DB: {DB_HOST}:{DB_PORT}/{DB_NAME}")
