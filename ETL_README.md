# Pipeline ETL iSaVigne → CRM

## 📋 Vue d'ensemble

Ce pipeline ETL (Extract, Transform, Load) automatise l'ingestion des données depuis iSaVigne (sans API) vers le système CRM de recommandations.

**Architecture:**
```
iSaVigne (source)
    ↓
Exports Excel/CSV → RAW
    ↓
ETL Python → STAGING → CURATED
    ↓
PostgreSQL (warehouse)
    ↓
Application (Dashboard + Reco)
```

---

## 🗂️ Structure des Dossiers

```
C:\Users\Valentin\Desktop\CRM_Ruhlmann\
exports/
├── raw/                    # 📥 Fichiers bruts (immuables)
│   └── isavigne/
│       ├── ventes_lignes/
│       │   └── ventes_lignes_2025-12-27.csv
│       ├── clients/
│       ├── produits/
│       ├── stock/
│       └── contacts/
├── staging/                # 🔄 Fichiers en cours de transformation
│   └── ventes_lignes_raw_20251227_120000.csv
├── curated/                # ✅ Données prêtes pour la base
│   └── VENTES_LIGNES_curated_20251227_120000.csv
├── config/                 # ⚙️ Configuration
│   ├── state.json          # État de synchro (dernières dates)
│   └── manifest_raw.json   # Suivi des fichiers traités
└── logs/                   # 📊 Logs d'exécution
    └── run_20251227_1200.log

crm-reco-platform/
etl/
├── __init__.py
├── config.py              # Configuration centrale
├── normalizers.py         # Fonctions de normalisation
├── ingest_raw.py          # Étape 1: Ingestion RAW
├── transform_sales.py     # Étape 2: Transformation ventes
├── create_schema.sql      # Schéma PostgreSQL
└── main.py               # Orchestration du pipeline
```

---

## 🚀 Démarrage Rapide

### 1. Initialiser la Base PostgreSQL

```bash
# Depuis Docker
docker exec -i crm-postgres psql -U crm_user -d crm_reco < etl/create_schema.sql

# Ou localement (si PostgreSQL est installé)
psql -U crm_user -d crm_reco -f etl/create_schema.sql
```

### 2. Préparer les Exports iSaVigne

Déposer les fichiers CSV/XLSX dans:
```
C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\<type_dataset>/
```

Exemple:
```
exports/raw/isavigne/ventes_lignes/ventes_lignes_2025-12-27.csv
exports/raw/isavigne/clients/clients_2025-12-27.csv
exports/raw/isavigne/produits/produits_2025-12-27.csv
```

### 3. Lancer le Pipeline

```bash
cd crm-reco-platform
python etl/main.py
```

Ou individuellement:

```bash
# Étape 1: Ingestion RAW → STAGING
python etl/ingest_raw.py

# Étape 2: Transformation STAGING → CURATED
python etl/transform_sales.py

# Étape 3: Chargement CURATED → PostgreSQL
python etl/load_postgres.py
```

---

## 📊 Modules ETL

### `config.py`
Configuration centralisée:
- Chemins des dossiers (RAW, STAGING, CURATED)
- Paramètres base de données
- Schémas de données attendus
- Règles de qualité
- Logging

**Usage:**
```python
from etl.config import RAW_DIR, STAGING_DIR, logger
```

### `normalizers.py`
Fonctions de normalisation des données:
- `normalize_client_code()` - Code client (uppercase, trim, pas d'accents)
- `normalize_produit_label()` - Clé produit stable
- `normalize_date()` - Conversion dates (ISO)
- `normalize_float()` - Montants (virgule → point)
- `normalize_email()` - Validation emails
- `create_document_id()` - Identifiant unique document
- `calculate_qty_unit()` - Conversion article → bouteilles

**Usage:**
```python
from etl.normalizers import normalize_client_code, normalize_produit_label

client_code = normalize_client_code("  CLIENT-001  ")
# → "CLIENT001"
```

### `ingest_raw.py`
**Étape 1: Détection et copie des fichiers RAW**

Fonctionnalités:
- Détecte les nouveaux fichiers RAW (CSV/XLSX)
- Valide le schéma attendu
- Vérifie la qualité (doublons, nulls)
- Copie en STAGING avec horodatage
- Met à jour un manifest (traçabilité)

**Functions principales:**
- `detect_raw_files(dataset_type)` - Liste les fichiers RAW
- `read_raw_file(filepath)` - Charge un fichier CSV/XLSX
- `validate_schema(df, schema)` - Vérifie les colonnes
- `check_data_quality(df)` - Statistiques qualité
- `ingest_dataset(dataset_type)` - Traite un dataset complet
- `ingest_all_datasets()` - Lance l'ingestion complète

**Exemple:**
```python
from etl.ingest_raw import ingest_all_datasets

results = ingest_all_datasets()
for dataset_type, r in results.items():
    print(f"{dataset_type}: {r['files_processed']} fichiers")
```

### `transform_sales.py`
**Étape 2: Transformation des données de ventes**

Fonctionnalités:
- Normalise tous les champs (codes, dates, montants)
- Crée les clés stables (Produit_Key, Document_ID)
- Calcule Qty_Unit (conversion articles)
- Applique les règles métier (exclusions, filtres)
- Enregistre en CURATED

**Functions principales:**
- `normalize_sales_columns(df)` - Normalise les colonnes brutes
- `create_derived_columns(df)` - Crée Produit_Key, Document_ID, Qty_Unit
- `apply_business_rules(df)` - Filtre et exclusions
- `transform_sales_data(input_file)` - Pipeline complet
- `process_all_sales_files()` - Traite tous les fichiers

**Exemple:**
```python
from etl.transform_sales import process_all_sales_files

results = process_all_sales_files()
print(f"Fichiers curated: {results['curated_files']}")
```

### `create_schema.sql`
**Initialisation de la base PostgreSQL**

Crée:
- Schéma `etl` (tables de staging)
  - `etl.ventes_lignes`
  - `etl.clients`
  - `etl.produits`
  - `etl.stock`
  - `etl.runs` (historique exécutions)

- Schéma `crm` (tables métier)
  - `crm.customer_360` (RFM + profil client)
  - `crm.recommendations` (recommandations générées)
  - `crm.contact_log` (logs d'envois)

- Indexes (performance)
- Permissions (user crm_user)

---

## 🔄 Flux de Données

### Cycle Standard (Hebdomadaire)

```
Lundi 06:00 → Export iSaVigne (RAW)
  ↓
Lundi 06:10 → Ingestion RAW → STAGING
  ↓
Lundi 06:15 → Transformation STAGING → CURATED
  ↓
Lundi 06:20 → Chargement CURATED → PostgreSQL
  ↓
Lundi 06:30 → Génération recommandations
  ↓
Lundi 06:45 → Envoi emails (optionnel)
```

### Contrôles Qualité

**À chaque étape:**
1. ✅ Détection des fichiers
2. ✅ Validation du schéma
3. ✅ Contrôle des doublons
4. ✅ Analyse des nulls
5. ✅ Règles métier
6. ✅ Logs complets

---

## ⚙️ Configuration

### Chemins d'Accès

**Windows (par défaut):**
```python
EXPORTS_ROOT = Path("C:\\Users\\Valentin\\Desktop\\CRM_Ruhlmann\\exports")
```

**À adapter dans `config.py` si différent:**
```python
EXPORTS_ROOT = Path(r"C:\Ton\Chemin\ici")
```

### Base de Données

**Via variables d'environnement:**
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=crm_reco
export DB_USER=crm_user
export DB_PASSWORD=secure_password
```

**Ou dans Docker:**
```bash
docker-compose.yml (déjà configuré)
```

### Schémas de Données

**À maintenir dans `config.py`:**

```python
VENTES_SCHEMA = {
    "client_code": "str",
    "date_livraison": "datetime",
    "produit_label": "str",
    # ... (voir config.py)
}
```

---

## 📈 Monitoring & Debugging

### Logs

Chaque exécution produit un log:
```
exports/logs/run_20251227_1200.log
```

**Contenu:**
```
2025-12-27 12:00:15 - root - INFO - === INGESTION RAW ===
2025-12-27 12:00:15 - root - INFO - Détecté 3 fichier(s)
2025-12-27 12:00:20 - root - INFO - Chargé 1500 lignes
2025-12-27 12:00:25 - root - INFO - Schéma validé
2025-12-27 12:00:30 - root - INFO - ✅ Succès: 1500 lignes en staging
```

### Manifest

**`config/manifest_raw.json`** - Suivi des fichiers traités:
```json
{
  "processed_files": {
    "C:\\...\\ventes_lignes_2025-12-27.csv": {
      "processed_at": "2025-12-27T12:00:30",
      "staging_path": "exports/staging/ventes_lignes_raw_20251227_120030.csv",
      "nb_rows": 1500
    }
  }
}
```

### État de Synchro

**`config/state.json`** - Dates de dernière synchro:
```json
{
  "last_sync_ventes": "2025-12-27",
  "last_sync_clients": "2025-12-27",
  "last_run_date": "2025-12-27T12:00:30",
  "last_run_success": true
}
```

---

## 🆘 Dépannage

### Problème: "Colonnes manquantes"

**Cause:** Le fichier iSaVigne n'a pas toutes les colonnes attendues.

**Solution:**
1. Vérifier le fichier iSaVigne
2. Ajouter les colonnes manquantes
3. Ou adapter le schéma dans `config.py` si colonne optionnelle

### Problème: "Connexion base échouée"

**Cause:** PostgreSQL ou Docker ne tourne pas.

**Solution:**
```bash
# Vérifier Docker
docker-compose ps

# Relancer si besoin
docker-compose down
docker-compose up -d postgres redis backend
```

### Problème: "Accès refusé au dossier"

**Cause:** Permissions Windows.

**Solution:**
```bash
# Via PowerShell (en admin)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📅 Planification Automatique (RPA)

Voir **Document Plan B** pour:
- Power Automate Desktop (RPA) - Automatiser les exports iSaVigne
- Planificateur de tâches Windows - Lancer le pipeline hebdomadaire

---

## 🔗 Étapes Suivantes

1. ✅ **ETL Pipeline** (vous êtes ici)
2. 📧 **Intégration Brevo** - Envoi emails automatiques
3. 📊 **Moteur de Recommandations** - Logique métier avancée
4. 🌐 **Déploiement VPS OVH** - Hébergement production
5. 🔐 **Authentification & Sécurité** - Contrôle d'accès

---

## 📞 Support

Pour des questions ou bugs:
1. Consulter les logs (`exports/logs/`)
2. Vérifier le manifest (`config/manifest_raw.json`)
3. Vérifier l'état de synchro (`config/state.json`)
4. Ouvrir une issue GitHub

---

**Dernière mise à jour:** 27/12/2025  
**Version:** 1.0  
**Auteur:** Projet CRM Ruhlmann
