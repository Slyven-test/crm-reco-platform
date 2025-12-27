# 🚀 Quick Test - Valider le Pipeline en 5 minutes

**Objectif:** Vérifier que le pipeline ETL fonctionne de bout en bout

**Durée:** ~5 minutes

---

## ✍️ Étape 1: Créer des Fichiers de Test

### 1.1 Créer les dossiers

```bash
# Sur Windows (PowerShell ou cmd)
mkdir -p "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\ventes_lignes"
mkdir -p "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\clients"
mkdir -p "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\produits"
```

### 1.2 Créer fichier ventes_lignes_2025-12-27.csv

**Chemin:** `C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\ventes_lignes\ventes_lignes_2025-12-27.csv`

**Contenu:**
```csv
client_code,date_livraison,produit_label,qty_line,pu_ht,mt_ht,mt_ttc,marge,document_type,document_no,article,email,code_postal,ville
CL001,2025-12-27,Cremant Alsace Extra Brut,1,8.50,8.50,10.20,2.00,VENTE,V0001,CREMANT,jean@test.fr,67000,Strasbourg
CL002,2025-12-27,Gewurztraminer Vendanges Tardives,2,15.00,30.00,36.00,8.00,VENTE,V0002,GEWURZ,marie@test.fr,75000,Paris
CL003,2025-12-27,Riesling Alsace,1,10.00,10.00,12.00,3.00,VENTE,V0003,RIESLING,pierre@test.fr,13000,Marseille
CL001,2025-12-27,Gewurztraminer VT,1,15.00,15.00,18.00,4.00,VENTE,V0004,GEWURZ2,jean@test.fr,67000,Strasbourg
```

### 1.3 Créer fichier clients_2025-12-27.csv

**Chemin:** `C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\clients\clients_2025-12-27.csv`

**Contenu:**
```csv
client_code,nom,prenom,email,telephone,adresse,code_postal,ville,pays
CL001,Dupont,Jean,jean@test.fr,0123456789,1 rue de l'Exemple,67000,Strasbourg,France
CL002,Martin,Marie,marie@test.fr,0987654321,2 avenue de Paris,75000,Paris,France
CL003,Bernard,Pierre,pierre@test.fr,0456789123,3 boulevard Marseille,13000,Marseille,France
```

### 1.4 Créer fichier produits_2025-12-27.csv

**Chemin:** `C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\produits\produits_2025-12-27.csv`

**Contenu:**
```csv
produit,article,millesime,famille_crm,sous_famille,macro_categorie,prix_ttc,price_band,premium_tier
Cremant Alsace Extra Brut,CREMANT,2023,Alsace,Effervescents,Aperitif,10.20,10-15,Standard
Gewurztraminer Vendanges Tardives,GEWURZ,2022,Alsace,Blancs,Premium,36.00,30-40,Premium
Gewurztraminer Vendanges Tardives,GEWURZ2,2021,Alsace,Blancs,Premium,36.00,30-40,Premium
Riesling Alsace,RIESLING,2023,Alsace,Blancs,Standard,12.00,10-15,Standard
```

---

## 🎯 Étape 2: Lancer le Pipeline

### 2.1 Ouvrir Terminal

```bash
# Ouvrir PowerShell ou CMD
# Aller au dossier du projet
cd C:\Windows\System32\crm-reco-platform
```

### 2.2 Lancer le Pipeline Complet

```bash
python etl/main.py
```

### 2.3 Attendre les Résultats

Tu verras:
```
======================================================================
  📊 DÉMARRAGE PIPELINE ETL COMPLET
======================================================================

🔵 ÉTAPE 1/3: INGESTION RAW → STAGING
...
🔵 ÉTAPE 2/3: TRANSFORMATION STAGING → CURATED
...
🔵 ÉTAPE 3/3: CHARGEMENT CURATED → PostgreSQL
...

🌟 PIPELINE COMPLET - RÉSUMÉ FINAL
======================================================================
  ✅ SUCCÈS COMPLET - Pipeline ETL Fonctionnel! 🚀
======================================================================
```

---

## 🔍 Étape 3: Vérifier les Résultats

### 3.1 Vérifier les Fichiers Générés

```bash
# Fichiers en STAGING
dir "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\staging\"
# Doit contenir: ventes_lignes_raw_*.csv, clients_raw_*.csv, produits_raw_*.csv

# Fichiers CURATED
dir "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\curated\"
# Doit contenir: VENTES_LIGNES_curated_*.csv, CLIENTS_curated_*.csv, etc.

# Logs d'exécution
dir "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\logs\"
# Doit contenir: run_*.log
```

### 3.2 Vérifier dans PostgreSQL

**Option 1: Ligne de commande**

```bash
# Vérifier les données dans PostgreSQL
docker exec crm-postgres psql -U crm_user -d crm_reco -c "SELECT COUNT(*) as total FROM etl.ventes_lignes;"

# Doit afficher: total
#                4     (4 lignes de ventes de test)
```

**Option 2: Depuis pgAdmin (interface web)**

```
http://localhost:5050
login: admin@example.com
password: admin

Servers > crm-reco > Databases > crm_reco > Schemas > etl > Tables
  - ventes_lignes (4 rows)
  - clients (3 rows)
  - produits (4 rows)
```

### 3.3 Lire les Logs

```bash
# Fichier de log principal
type "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\logs\run_*.log"

# Tu verras quelque chose comme:
# 2025-12-27 16:00:15 - root - INFO - === INGESTION RAW ===
# 2025-12-27 16:00:15 - root - INFO - Détecté 3 fichier(s)
# 2025-12-27 16:00:20 - root - INFO - ✅ Succès: 4 lignes en staging
```

---

## ✅ Checklist de Succès

- [ ] Fichiers de test créés dans `exports/raw/isavigne/`
- [ ] Pipeline lancé: `python etl/main.py`
- [ ] Message "✅ SUCCÈS COMPLET" affiché
- [ ] Fichiers STAGING créés (`exports/staging/`)
- [ ] Fichiers CURATED créés (`exports/curated/`)
- [ ] Logs générés (`exports/logs/`)
- [ ] PostgreSQL contient les données (4 ventes, 3 clients, 4 produits)
- [ ] Pas d'erreurs dans les logs

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'"

```bash
# Installer les dépendances
pip install -r requirements.txt
```

### "Connexion PostgreSQL échouée"

```bash
# Vérifier que PostgreSQL est lancé
docker-compose ps postgres

# Relancer si besoin
docker-compose restart postgres

# Attendre 5 secondes et réessayer
```

### "Dossiers RAW introuvables"

```bash
# Créer la structure complète
mkdir -p "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\{ventes_lignes,clients,produits}"
```

### "Aucun fichier CURATED détecté"

Le fichier CSV doit être bien formaté:
- Colonnes en minuscules avec underscores
- Valeurs numériques avec point (pas de virgule)
- Dates au format YYYY-MM-DD
- Vérifier les logs pour les colonnes attendues

---

## 👀 Précisions Importées de Test

### Doublons Simulés

Le fichier de test contient:
- 1 doublon dans les ventes (CL001 avec 2 produits différents)
- Tu verras: "⚠️ Doublons détectés: 0" (car les produits sont différents)

### Transformations Appliquées

Le pipeline va:
1. Normaliser les codes clients (trim, uppercase)
2. Créer produit_key (de "Cremant Alsace Extra Brut" → "CREMANT ALSACE EXTRA BRUT")
3. Créer document_id (de document_no et client_code)
4. Calculer qty_unit (conversion articles en unités)

### Vérifier une Ligne Transformée

```bash
# Ouvrir le fichier CURATED
type "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\curated\VENTES_LIGNES_curated_*.csv"

# Tu verras des colonnes supplémentaires:
#   - produit_key (normalisé)
#   - document_id (créé)
#   - qty_unit (converti)
```

---

## 🔗 Données Chargées en Base

### Table: etl.ventes_lignes

```sql
SELECT * FROM etl.ventes_lignes LIMIT 5;

-- Doit retourner 4 lignes avec:
--   client_code: CL001, CL002, CL003, CL001
--   produit_key: CREMANT ALSACE EXTRA BRUT, etc.
--   mt_ht: 8.50, 30.00, 10.00, 15.00
```

### Table: etl.clients

```sql
SELECT client_code, nom, email FROM etl.clients;

-- Doit retourner 3 lignes:
--   CL001, Dupont, jean@test.fr
--   CL002, Martin, marie@test.fr
--   CL003, Bernard, pierre@test.fr
```

### Table: etl.produits

```sql
SELECT produit_key, prix_ttc FROM etl.produits;

-- Doit retourner 4 lignes de produits
```

---

## 🌟 Prochaines Étapes (Après Test)

1. **Tester avec données réelles iSaVigne**
   - Exporter vraies données iSaVigne
   - Placer dans `exports/raw/isavigne/`
   - Lancer pipeline

2. **Valider la qualité**
   - Vérifier les transformations
   - Consulter les logs pour anomalies

3. **Configurer Power Automate Desktop**
   - Automatiser les exports iSaVigne
   - Scheduler l'exécution hebdomadaire

4. **Intégrer Brevo**
   - Créer module de synchronisation
   - Templates d'emails

---

## 🋡️ Architecture Testée

```
RAW files (Test)
    ↓
ETL Pipeline (ingest → transform → load)
    ↓
STAGING files (Test files with timestamp)
    ↓
CURATED files (Transformed & normalized)
    ↓
PostgreSQL (Data loaded)
    ✓ VERIFY with SQL queries
```

---

## 📝 Notes

- Les fichiers de test sont **minimalistes** mais complets
- Le pipeline applique **les mêmes transformations** que les vraies données
- Les logs **tracent chaque étape** pour debug facile
- Les doublons sont **automatiquement détectés et supprimés**
- PostgreSQL **accepte les données immédiatement**

---

**Si tout fonctionne ✅, le pipeline est prêt pour les données réelles!** 🚀

*Durée test: ~5 minutes*  
*Durée réelles données: variable selon volume*
