-- ============================================================================
-- SCHEMA PostgreSQL pour ETL CRM iSaVigne
-- Version: 1.0
-- Auteur: Projet CRM Ruhlmann
-- ============================================================================

-- Les tables pour les données stockées

CREATE SCHEMA IF NOT EXISTS etl;
CREATE SCHEMA IF NOT EXISTS crm;

-- ============================================================================
-- Tables ETL (staging de données brutes/transformées)
-- ============================================================================

-- Historique des executions ETL
CREATE TABLE IF NOT EXISTS etl.runs (
    run_id SERIAL PRIMARY KEY,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_type VARCHAR(50),  -- 'ingest', 'transform', 'quality', 'load'
    status VARCHAR(20),    -- 'started', 'success', 'failed'
    duration_seconds INT,
    rows_processed INT,
    rows_failed INT,
    error_message TEXT
);

-- Données de ventes chargées
CREATE TABLE IF NOT EXISTS etl.ventes_lignes (
    vente_id SERIAL PRIMARY KEY,
    client_code VARCHAR(100),
    date_livraison DATE,
    document_id VARCHAR(255),
    produit_key VARCHAR(255),
    produit_label VARCHAR(500),
    article VARCHAR(100),
    qty_line NUMERIC(10, 2),
    qty_unit NUMERIC(10, 2),
    pu_ht NUMERIC(12, 2),
    mt_ht NUMERIC(12, 2),
    mt_ttc NUMERIC(12, 2),
    marge NUMERIC(12, 2),
    document_type VARCHAR(50),
    document_no VARCHAR(50),
    email VARCHAR(255),
    code_postal VARCHAR(10),
    ville VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, produit_key, client_code)
);

-- Clients importés
CREATE TABLE IF NOT EXISTS etl.clients (
    client_id SERIAL PRIMARY KEY,
    client_code VARCHAR(100) UNIQUE,
    nom VARCHAR(255),
    prenom VARCHAR(255),
    email VARCHAR(255),
    telephone VARCHAR(20),
    adresse VARCHAR(500),
    code_postal VARCHAR(10),
    ville VARCHAR(200),
    pays VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Produits importés
CREATE TABLE IF NOT EXISTS etl.produits (
    produit_id SERIAL PRIMARY KEY,
    produit_key VARCHAR(255) UNIQUE,
    produit VARCHAR(500),
    article VARCHAR(100),
    millesime VARCHAR(20),
    famille_crm VARCHAR(100),
    sous_famille VARCHAR(100),
    macro_categorie VARCHAR(100),
    prix_ttc NUMERIC(10, 2),
    price_band VARCHAR(50),
    premium_tier VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stock importé
CREATE TABLE IF NOT EXISTS etl.stock (
    stock_id SERIAL PRIMARY KEY,
    produit_key VARCHAR(255),
    stock_total NUMERIC(12, 2),
    stock_reserve NUMERIC(12, 2),
    date_snapshot DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(produit_key) REFERENCES etl.produits(produit_key)
);

-- ============================================================================
-- Tables CRM (données métier et recommandations)
-- ============================================================================

-- Vue consolidée des clients avec métriques
CREATE TABLE IF NOT EXISTS crm.customer_360 (
    customer_id SERIAL PRIMARY KEY,
    client_code VARCHAR(100) UNIQUE REFERENCES etl.clients(client_code),
    total_achats NUMERIC(12, 2),
    nb_achats INT,
    recency_days INT,  -- jours depuis dernier achat
    frequency_purchases INT,
    monetary_value NUMERIC(12, 2),
    famille_preference VARCHAR(255),
    dernier_contact DATE,
    nb_emails_sent INT,
    nb_bounces INT,
    opt_out BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recommandations générées
CREATE TABLE IF NOT EXISTS crm.recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    client_code VARCHAR(100) REFERENCES etl.clients(client_code),
    produit_key_1 VARCHAR(255) REFERENCES etl.produits(produit_key),
    produit_key_2 VARCHAR(255) REFERENCES etl.produits(produit_key),
    produit_key_3 VARCHAR(255) REFERENCES etl.produits(produit_key),
    scenario VARCHAR(50),  -- 'rebuy', 'cross-sell', 'winback'
    reason_1 VARCHAR(255),
    reason_2 VARCHAR(255),
    reason_3 VARCHAR(255),
    score_1 NUMERIC(5, 2),
    score_2 NUMERIC(5, 2),
    score_3 NUMERIC(5, 2),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    status VARCHAR(20)  -- 'pending', 'sent', 'clicked', 'converted'
);

-- Log de contacts envoyés
CREATE TABLE IF NOT EXISTS crm.contact_log (
    contact_id SERIAL PRIMARY KEY,
    client_code VARCHAR(100) REFERENCES etl.clients(client_code),
    email VARCHAR(255),
    channel VARCHAR(50),  -- 'email', 'sms'
    scenario VARCHAR(50),
    produit_key VARCHAR(255),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20),  -- 'ok', 'bounce', 'opt-out', 'failed'
    description TEXT
);

-- ============================================================================
-- INDEXES (pour performance)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_ventes_client_code ON etl.ventes_lignes(client_code);
CREATE INDEX IF NOT EXISTS idx_ventes_date ON etl.ventes_lignes(date_livraison);
CREATE INDEX IF NOT EXISTS idx_ventes_produit_key ON etl.ventes_lignes(produit_key);
CREATE INDEX IF NOT EXISTS idx_ventes_document_id ON etl.ventes_lignes(document_id);

CREATE INDEX IF NOT EXISTS idx_clients_code ON etl.clients(client_code);
CREATE INDEX IF NOT EXISTS idx_produits_key ON etl.produits(produit_key);

CREATE INDEX IF NOT EXISTS idx_recommendations_client ON crm.recommendations(client_code);
CREATE INDEX IF NOT EXISTS idx_contact_log_client ON crm.contact_log(client_code);
CREATE INDEX IF NOT EXISTS idx_contact_log_date ON crm.contact_log(sent_at);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA etl TO crm_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA crm TO crm_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA etl TO crm_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA crm TO crm_user;

-- ============================================================================
-- AFFICHAGE CONFIRMATION
-- ============================================================================

SELECT 'Schema ETL et CRM créés avec succès' AS message;
