# 🚀 Getting Started - Guide Rapide

**Bienvenue!** Ce guide te montre comment démarrer avec le CRM iSaVigne en 5 minutes.

---

## ⚡ Prérequis

- ✅ Docker & Docker Compose installés
- ✅ Git clonné: `crm-reco-platform`
- ✅ Port 80, 8000, 5432, 6379 libres (ou configurable)
- ✅ Python 3.11+ (optionnel, pour tests locaux)

---

## 🎯 Démarrage Rapide (5 min)

### 1️⃣ Vérifie l'application est lancée

```bash
cd C:\Windows\System32\crm-reco-platform
docker-compose ps
```

Tu devrais voir:
```
NAME            STATUS
crm-frontend    Up (healthy)
crm-backend     Up (healthy)
crm-postgres    Up (healthy)
crm-redis       Up (healthy)
```

### 2️⃣ Accède à l'application

**Dashboard (Frontend):**
```
http://localhost
```

**API Swagger (Documentation):**
```
http://localhost:8000/docs
```

**Health Check (Backend):**
```
http://localhost:8000/health
```

### 3️⃣ Crée tes premiers fichiers d'export

Crée un fichier **test** pour valider le pipeline:

```bash
# Crée le dossier
mkdir -p "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\ventes_lignes"

# Crée un fichier CSV de test
echo "client_code,date_livraison,produit_label,qty_line,pu_ht,mt_ht,mt_ttc,marge,document_type,document_no,article" > ventes_lignes_2025-12-27.csv
echo "C001,27/12/2025,Cremant Alsace,1,8.5,8.5,10.2,2.0,VENTE,V001,CREMANT" >> ventes_lignes_2025-12-27.csv
```

### 4️⃣ Lance le pipeline ETL

```bash
# Depuis le répertoire du projet
cd C:\Windows\System32\crm-reco-platform

# Étape 1: Ingestion RAW
python etl/ingest_raw.py

# Étape 2: Transformation
python etl/transform_sales.py

# Vérifie les résultats
ls exports/curated/
ls exports/logs/
```

---

## 📊 Les Trois Étapes du Pipeline

### Étape 1: Ingestion RAW (10-15 secondes)
```
RAW files → Détection → Validation → Copie en STAGING
```

**Logs:**
```
=== INGESTION RAW ===
Détecté 3 fichier(s)
Trait ventes_lignes_2025-12-27.csv
  Chargé: 100 lignes brutes
  Schéma validé
  ✅ Succès: 100 lignes en staging
```

### Étape 2: Transformation (5-10 secondes)
```
STAGING files → Normalisation → Clés dérivées → CURATED
```

**Logs:**
```
=== TRANSFORMATION VENTES ===
Détecté 1 fichier(s) de ventes en staging
Transform ventes: ventes_lignes_raw_20251227_120000.csv
  Chargé: 100 lignes brutes
  Normalisation des colonnes...
  Création des colonnes dérivées...
  Application des règles métier...
  ✅ Sauvegardé en curated: VENTES_LIGNES_curated_20251227_120000.csv
```

### Étape 3: Chargement en Base (À faire)
```
CURATED files → Nettoyage → PostgreSQL
```

---

## 📁 Fichiers Générés

Après les étapes 1 et 2, tu auras:

```
exports/
├── raw/
│   └── isavigne/
│       └── ventes_lignes/
│           └── ventes_lignes_2025-12-27.csv     ← Ton fichier original
├── staging/
│   └── ventes_lignes_raw_20251227_120000.csv    ← Copie avec horodatage
├── curated/
│   └── VENTES_LIGNES_curated_20251227_120000.csv ← Données transformées
├── config/
│   ├── state.json                               ← État de synchro
│   └── manifest_raw.json                        ← Suivi des fichiers
└── logs/
    └── run_20251227_1200.log                    ← Logs complets
```

---

## 🎨 Explorer le Dashboard

### Pages Disponibles

1. **Dashboard** (page d'accueil)
   - Vue d'ensemble
   - KPIs (Total recommendations, Customers, Approval Rate)
   - Charge de travail

2. **Recommendations**
   - Recherche de recommandations
   - Filtres (client, produit, date)
   - Résultats détaillés

3. **Approvals**
   - Validation des recommandations
   - Status du processus

4. **Quality**
   - Métriques de qualité
   - Coverage et Accuracy

5. **Compliance**
   - Gating rules
   - Conformité RGPD

6. **Settings**
   - Configuration
   - Paramètres du système

---

## 🔧 Configuration

### Chemins d'Accès

Si tu veux changer le chemin des exports:

```python
# Dans etl/config.py
EXPORTS_ROOT = Path(r"C:\Ton\Chemin\Personnalisé")
```

### Base de Données

Pour changer les identifiants PostgreSQL:

```bash
# Via variables d'environnement
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=crm_reco
set DB_USER=crm_user
set DB_PASSWORD=ton_mot_de_passe
```

---

## 📝 Fichiers de Test Minimal

### Crée les fichiers de test rapidement:

**ventes_lignes_2025-12-27.csv:**
```csv
client_code,date_livraison,produit_label,qty_line,pu_ht,mt_ht,mt_ttc,marge,document_type,document_no,article,email,code_postal,ville
CL001,27/12/2025,Crémant Alsace Extra Brut,1,8.50,8.50,10.20,2.00,VENTE,V0001,CREMANT,jean@example.com,67000,Strasbourg
CL002,27/12/2025,Gewurztraminer Vendanges Tardives,2,15.00,30.00,36.00,8.00,VENTE,V0002,GEWURZ,marie@example.com,75000,Paris
CL003,27/12/2025,Riesling Alsace,1,10.00,10.00,12.00,3.00,VENTE,V0003,RIESLING,pierre@example.com,13000,Marseille
```

**clients_2025-12-27.csv:**
```csv
client_code,nom,prenom,email,telephone,adresse,code_postal,ville,pays
CL001,Dupont,Jean,jean@example.com,0123456789,1 rue de l'Exemple,67000,Strasbourg,France
CL002,Martin,Marie,marie@example.com,0987654321,2 avenue de Paris,75000,Paris,France
CL003,Bernard,Pierre,pierre@example.com,0456789123,3 boulevard Marseille,13000,Marseille,France
```

**produits_2025-12-27.csv:**
```csv
produit,article,millesime,famille_crm,sous_famille,macro_categorie,prix_ttc,price_band,premium_tier
Crémant Alsace Extra Brut,CREMANT,2023,Alsace,Effervescents,Apéritif,10.20,10-15,Standard
Gewurztraminer Vendanges Tardives,GEWURZ,2022,Alsace,Blancs,Premium,36.00,30-40,Premium
Riesling Alsace,RIESLING,2023,Alsace,Blancs,Standard,12.00,10-15,Standard
```

---

## 🐛 Dépannage

### "Port déjà en utilisation"

```bash
# Arrête les conteneurs
docker-compose down

# Relance
docker-compose up -d
```

### "Erreur de connexion PostgreSQL"

```bash
# Vérifie que PostgreSQL est bien lancé
docker-compose ps postgres

# Relance si nécessaire
docker-compose restart postgres

# Attends 5 secondes et réessaie
```

### "Fichier not found"

```bash
# Assure-toi que le chemin existe
dir "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports"

# Crée s'il manque
mkdir -p "C:\Users\Valentin\Desktop\CRM_Ruhlmann\exports\raw\isavigne\{ventes_lignes,clients,produits}"
```

### "Python ModuleNotFoundError"

```bash
# Installe les dépendances
pip install -r requirements.txt

# Ou avec venv
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📚 Documentation Complète

Pour plus de détails:
- **ETL Pipeline:** [ETL_README.md](ETL_README.md)
- **Project Status:** [PROJET_STATUS.md](PROJET_STATUS.md)
- **Plan Complet:** [Plan B iSaVigne](file:5)

---

## ✅ Checklist Démarrage

- [ ] Docker Compose lancé
- [ ] Frontend accessible sur http://localhost
- [ ] Backend API accessible sur http://localhost:8000/docs
- [ ] Fichiers de test créés dans exports/raw/isavigne/
- [ ] ETL pipeline exécuté avec succès
- [ ] Fichiers générés en staging/ et curated/
- [ ] Logs vérifiés dans exports/logs/
- [ ] Base PostgreSQL initialisée

---

## 🎉 Prochaines Étapes

1. **Tester avec tes données iSaVigne** (pas juste de test)
2. **Valider la qualité des transformations**
3. **Créer un script d'automatisation** (RPA / Task Scheduler)
4. **Intégrer Brevo** pour les emails
5. **Déployer sur VPS OVH** quand prêt

---

**Bon démarrage! 🚀**

Si tu as des questions, consulte la documentation ou ouvre une issue sur GitHub.

*Dernière mise à jour: 27/12/2025*
