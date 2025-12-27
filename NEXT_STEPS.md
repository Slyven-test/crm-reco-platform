# 🔥 PROCHAINES ÉTAPES - Plan Détaillé

**Date:** 27/12/2025  
**Statut:** 🚧 Phase ETL 1 terminée - 2/3 modules prêts

Le document **Plan B iSaVigne** te fournit la stratégie complète. Voici les étapes concrètes à faire maintenant, dans l'ordre.

---

## 🚧 ÉTAPE 1: Finaliser le Pipeline ETL (Jeudi - Vendredi)

### 1.1 Créer `load_postgres.py` (Chargement en BD)

**Objectif:** Charger les données CURATED transformées dans PostgreSQL.

**À faire:**
```python
# etl/load_postgres.py

import pandas as pd
from sqlalchemy import create_engine
from etl.config import DATABASE_URL, logger

def load_table(table_name, csv_file):
    """
    Charge un fichier CSV dans une table PostgreSQL
    
    Args:
        table_name: nom de la table cible (ex: 'etl.ventes_lignes')
        csv_file: chemin du fichier CURATED
    
    Returns:
        dict avec statut de chargement
    """
    try:
        # Charger le CSV
        df = pd.read_csv(csv_file, dtype={'client_code': str, 'produit_key': str})
        
        # Connexion PostgreSQL
        engine = create_engine(DATABASE_URL)
        
        # Détection des doublons par clé naturelle
        # Pour ventes: (document_id, produit_key, client_code)
        if table_name == 'etl.ventes_lignes':
            key_cols = ['document_id', 'produit_key', 'client_code']
            df_dedup = df.drop_duplicates(subset=key_cols, keep='last')
            nb_dupes = len(df) - len(df_dedup)
            if nb_dupes > 0:
                logger.warning(f"Détecté {nb_dupes} doublons sur {table_name}")
            df = df_dedup
        
        # Chargement
        df.to_sql(
            table_name.split('.')[1],  # nom table
            engine,
            schema=table_name.split('.')[0],  # schéma
            if_exists='append',  # ajouter, ne pas remplacer
            index=False,
            chunksize=500  # par lots
        )
        
        logger.info(f"✓ Chargé {len(df)} lignes dans {table_name}")
        return {'success': True, 'rows_loaded': len(df), 'duplicates_removed': nb_dupes}
        
    except Exception as e:
        logger.error(f"✗ Erreur chargement {table_name}: {str(e)}")
        return {'success': False, 'error': str(e)}

def load_all_curated():
    """
    Charge tous les fichiers curated en PostgreSQL
    """
    from pathlib import Path
    from etl.config import CURATED_DIR
    
    results = {}
    curated_files = list(CURATED_DIR.glob('*.csv'))
    
    for csv_file in curated_files:
        # Déterminer le nom de la table à partir du nom du fichier
        if 'VENTES_LIGNES' in csv_file.name:
            table_name = 'etl.ventes_lignes'
        elif 'CLIENTS' in csv_file.name:
            table_name = 'etl.clients'
        elif 'PRODUITS' in csv_file.name:
            table_name = 'etl.produits'
        elif 'STOCK' in csv_file.name:
            table_name = 'etl.stock'
        else:
            logger.warning(f"Fichier curated non reconnu: {csv_file.name}")
            continue
        
        results[table_name] = load_table(table_name, str(csv_file))
    
    return results

if __name__ == '__main__':
    logger.info("=== CHARGEMENT CURATED → PostgreSQL ===")
    results = load_all_curated()
    for table, result in results.items():
        if result['success']:
            print(f"✓ {table}: {result['rows_loaded']} lignes")
        else:
            print(f"✗ {table}: {result['error']}")
```

### 1.2 Créer `main.py` (Orchestration)

**Objectif:** Orchestrer tout le pipeline (ingest → transform → load) en une seule commande.

**À faire:**
```python
# etl/main.py

import time
from datetime import datetime
from etl.config import logger
from etl.ingest_raw import ingest_all_datasets
from etl.transform_sales import process_all_sales_files
from etl.load_postgres import load_all_curated

def run_etl_pipeline():
    """
    Orchestre le pipeline ETL complet:
    1. Ingestion RAW → STAGING
    2. Transformation STAGING → CURATED
    3. Chargement CURATED → PostgreSQL
    """
    start_time = time.time()
    
    try:
        logger.info("\n" + "="*60)
        logger.info("📊 DÉMARRAGE PIPELINE ETL COMPLET")
        logger.info(f"Date/Heure: {datetime.now().isoformat()}")
        logger.info("="*60 + "\n")
        
        # ÉTAPE 1: Ingestion
        logger.info("\n🔵 ÉTAPE 1/3: INGESTION RAW → STAGING")
        ingest_results = ingest_all_datasets()
        logger.info(f"Résultats ingestion: {ingest_results}")
        
        # ÉTAPE 2: Transformation
        logger.info("\n🔵 ÉTAPE 2/3: TRANSFORMATION STAGING → CURATED")
        transform_results = process_all_sales_files()
        logger.info(f"Résultats transformation: {transform_results}")
        
        # ÉTAPE 3: Chargement
        logger.info("\n🔵 ÉTAPE 3/3: CHARGEMENT CURATED → PostgreSQL")
        load_results = load_all_curated()
        logger.info(f"Résultats chargement: {load_results}")
        
        # Résumé final
        duration = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info(f"✅ SUCCÈS COMPLET en {duration:.2f}s")
        logger.info("="*60 + "\n")
        
        return {
            'success': True,
            'duration': duration,
            'ingest': ingest_results,
            'transform': transform_results,
            'load': load_results
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"\n❌ ERREUR PIPELINE après {duration:.2f}s: {str(e)}", exc_info=True)
        return {
            'success': False,
            'duration': duration,
            'error': str(e)
        }

if __name__ == '__main__':
    result = run_etl_pipeline()
    exit(0 if result['success'] else 1)
```

### 1.3 Tester avec Données de Test

**Créer les fichiers de test:**

```bash
# Dossiers
mkdir -p "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\{ventes_lignes,clients,produits,stock}"

# Créer ventes_lignes_2025-12-27.csv
echo "client_code,date_livraison,produit_label,qty_line,pu_ht,mt_ht,mt_ttc,marge,document_type,document_no,article,email,code_postal,ville" > ventes_lignes_2025-12-27.csv
echo "CL001,27/12/2025,Cremant Alsace Extra Brut,1,8.5,8.5,10.2,2.0,VENTE,V0001,CREMANT,jean@test.fr,67000,Strasbourg" >> ventes_lignes_2025-12-27.csv
echo "CL002,27/12/2025,Gewurztraminer VT,2,15.0,30.0,36.0,8.0,VENTE,V0002,GEWURZ,marie@test.fr,75000,Paris" >> ventes_lignes_2025-12-27.csv
```

**Exécuter le pipeline:**

```bash
cd C:\Windows\System32\crm-reco-platform
python etl/main.py
```

**Vérifier les résultats:**

```bash
# Vérifier les fichiers générés
dir exports\staging\        # fichiers horodatés
dir exports\curated\        # fichiers transformés
dir exports\logs\           # logs d'exécution

# Vérifier la base PostgreSQL
docker exec crm-postgres psql -U crm_user -d crm_reco -c "SELECT COUNT(*) FROM etl.ventes_lignes;"
```

---

## 🚧 ÉTAPE 2: Intégration Brevo (Lundi - Mercredi)

### 2.1 Module de Synchronisation Brevo

**Objectif:** Envoyer les recommandations via email via la plateforme Brevo (anciennement Sendinblue).

**À créer:** `etl/brevo_integration.py`

**Fonctionnalités:**
- Authentification API Brevo
- Upload contacts
- Envoi emails personnalisés
- Log des statuts (ok, bounce, opt-out)

### 2.2 Templates d'Emails

**À créer:**
- Template rebuy (racheter un produit acheté)
- Template cross-sell (produit complémentaire)
- Template winback (réactiver client inactif)

### 2.3 Scheduleur d'Envois

**À créer:** Déclencher les envois à partir du dashboard avec validation.

---

## 🚧 ÉTAPE 3: Moteur de Recommandations (Mercredi - Jeudi)

### 3.1 Analyse RFM

**À créer:** Scoring basé sur Recency, Frequency, Monetary Value.

**Table résultante:** `crm.rfm_scores`

### 3.2 Scoring Co-achats

**À créer:** Identifier les paires de produits achetées ensemble (cross-sell).

### 3.3 Recommendations Candidate

**À créer:** Table `crm.recommendations` avec produits proposés et score.

---

## 🚧 ÉTAPE 4: Automatisation (Power Automate Desktop)

### 4.1 Créer Flow PAD pour Exports iSaVigne

**Objectif:** Automatiser les exports depuis iSaVigne vers le dossier RAW.

**Procédure:**
1. Ouvrir Power Automate Desktop
2. Créer flow: "EXPORT_ISAVIGNE_HEBDO"
3. Enregistrer les étapes manuellement
4. Planifier via Planificateur de tâches Windows

### 4.2 Planifier Exécution

**Planificateur de tâches:**
- **Jour:** Lundi
- **Heure:** 06:00
- **Actions:**
  1. Exports iSaVigne (PAD)
  2. Lancer pipeline ETL (python etl/main.py)
  3. Générer recommandations
  4. Envoyer emails (Brevo)

---

## 🎯 DÉPLOIEMENT VPS OVH (Semaine prochaine)

### 5.1 Préparation

- [ ] Commander VPS OVH (2-4 vCPU, 4-8GB RAM, 40GB SSD)
- [ ] Setup Ubuntu 22.04 LTS
- [ ] Installer Docker & Docker Compose
- [ ] Domaine personnalisé (ex: crm.ruhlmann.fr)
- [ ] SSL/HTTPS via Let's Encrypt

### 5.2 Déploiement

- [ ] Pusher code sur GitHub
- [ ] Cloner sur VPS
- [ ] Lancer `docker-compose up -d`
- [ ] Configurer nginx reverse proxy
- [ ] Tests d'accès

### 5.3 Production Readiness

- [ ] Sauvegardes base PostgreSQL (quotidiennes)
- [ ] Monitoring uptime
- [ ] Logs centralisés
- [ ] Plan de récupération catastrophe

---

## ✅ Checklist Cette Semaine

### Jeudi (Aujourd'hui/Demain)

- [ ] `load_postgres.py` écrit et testé
- [ ] `main.py` écrit et testé
- [ ] Pipeline ETL complet fonctionnel (ingest → transform → load)
- [ ] Données de test chargées en PostgreSQL
- [ ] Logs vérifiés (pas d'erreur)

### Vendredi

- [ ] Tester avec données réelles iSaVigne (petit extrait si possible)
- [ ] Valider la qualité des transformations
- [ ] Documenter les anomalies découvertes
- [ ] Préparer rapport "Data Health" pour le dashboard

### Lundi (Semaine prochaine)

- [ ] Démarrer intégration Brevo
- [ ] Créer templates d'emails
- [ ] Commencer le moteur de recommandations

---

## 📄 Fichiers à Créer/Modifier

### À créer:
- ✅ `etl/config.py` ✓ FAIT
- ✅ `etl/normalizers.py` ✓ FAIT
- ✅ `etl/ingest_raw.py` ✓ FAIT
- ✅ `etl/transform_sales.py` ✓ FAIT
- ✅ `etl/create_schema.sql` ✓ FAIT
- 🔴 `etl/load_postgres.py` ← **À FAIRE IMMÉDIATEMENT**
- 🔴 `etl/main.py` ← **À FAIRE IMMÉDIATEMENT**

### À créer après:
- `etl/brevo_integration.py`
- `etl/recommendations_engine.py`
- `etl/quality_checks.py` (optionnel mais recommandé)
- `backend/routes/recommendations.py` (endpoint API)

---

## 📈 Architecture Finale (Semaine 2)

```
┌─────────────────────────────────────────────┐
│       iSaVigne (source)                     │
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────┴──────────────┐
       │ Power Automate Desktop   │ (RPA)
       │ Flow: EXPORT_ISAVIGNE    │
       └───────────┬──────────────┘
                   │
           Lundi 06:00 (auto)
                   │
       ┌───────────▼──────────────┐
       │ Exports CSV/XLSX         │
       │ → RAW folder             │
       └───────────┬──────────────┘
                   │
       ┌───────────▼──────────────┐
       │ ETL Pipeline (Python)    │
       │  1. Ingest              │
       │  2. Transform           │
       │  3. Load PostgreSQL     │
       └───────────┬──────────────┘
                   │
       ┌───────────▼──────────────┐
       │ PostgreSQL Warehouse     │
       │ - etl.ventes_lignes     │
       │ - etl.clients           │
       │ - etl.produits          │
       │ - crm.customer_360      │
       │ - crm.recommendations   │
       └───────────┬──────────────┘
                   │
       ┌───────────▼──────────────┐
       │ Recommendation Engine    │
       │ (RFM + Cross-sell)       │
       └───────────┬──────────────┘
                   │
       ┌───────────▼──────────────┐
       │ Brevo Integration        │
       │ (Email campaigns)        │
       └───────────┬──────────────┘
                   │
       ┌───────────▼──────────────┐
       │ Frontend Dashboard       │
       │ - Data Health           │
       │ - Recommendations       │
       │ - Approvals            │
       │ - Compliance           │
       └──────────────────────────┘
```

---

## 📝 Notes Importantes

1. **Sans API iSaVigne:** Le plan B (exports + RPA) est robuste et scalable.

2. **Qualité > Vitesse:** Les erreurs de données entraînent de mauvaises recommandations.

3. **Automatisation:** Une fois configurée, tout tourne tous les lundis sans intervention.

4. **Incrémental:** Ne pas recharger les 5 ans d'historique, seulement les nouveautés.

5. **Traçabilité:** Les logs permettent de retracer chaque ligne → très utile en débug.

---

## 🔗 Ressources

- **Plan Complet:** [Plan B iSaVigne](file:5)
- **Documentation ETL:** [ETL_README.md](ETL_README.md)
- **Quick Start:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **Status Projet:** [PROJET_STATUS.md](PROJET_STATUS.md)

---

**Dernière mise à jour:** 27/12/2025 16:25 CET  
**Prochaine étape:** Créer `load_postgres.py` et `main.py`  
**Deadline:** Jeudi 28/12/2025
