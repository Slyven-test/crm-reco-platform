# Database Setup and Management

## Overview

The CRM Recommendation Platform uses **PostgreSQL 16** with **SQLAlchemy ORM** for data access and **Alembic** for schema migrations.

## Core Tables

### Product & Catalog
- **product** - Product dimension with aroma profiles and metadata
- **product_alias** - Mapping from normalized labels to product keys

### Customer & Transactions
- **customer** - Customer master dimension (deduped)
- **order_line** - Normalized sales transactions
- **contact_event** - Contact history for silence window tracking

### Feature Engineering
- **client_master_profile** - Consolidated RFM, preferences, and aroma profiles

### Recommendations
- **reco_run** - Metadata for each recommendation run
- **reco_item** - Individual recommendations (rank 1..3 per customer)
- **audit_item** - Audit flags and validation issues

### Outcomes & Attribution
- **outcome_event** - Campaign purchase outcomes for learning

## Getting Started

### 1. Local Development Setup

#### With Docker (Recommended)

```bash
# Start database only
docker compose up -d db

# Check status
docker compose ps

# Initialize tables
python scripts/init_db.py --init
```

#### Without Docker

```bash
# Install PostgreSQL 16
# https://www.postgresql.org/download/

# Create database
psql -U postgres -c "CREATE DATABASE crm_reco_platform_dev;"

# Copy .env.example to .env and update DATABASE_URL
cp .env.example .env

# Initialize tables
python scripts/init_db.py --init
```

### 2. Database Initialization

```bash
# Initialize (create all tables)
python scripts/init_db.py --init

# Output should show:
# ✓ Database initialized successfully
#   - product
#   - customer
#   - order_line
#   - ... etc
```

## Using Alembic Migrations

### View Migration Status

```bash
# Current schema version
alembic current

# Migration history
alembic history
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision>

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision>
```

### Create New Migrations

When you modify models, create a migration:

```bash
# Auto-detect model changes
alembic revision --autogenerate -m "Add new table"

# Review generated migration in alembic/versions/
# Edit if needed

# Apply migration
alembic upgrade head
```

## Schema Reference

### Product Table

| Column | Type | Notes |
|--------|------|-------|
| product_key | VARCHAR(255) | Primary key, unique identifier |
| product_label | VARCHAR(512) | Human-readable name, unique |
| family_crm | VARCHAR(255) | Wine family (Red, White, Rosé, etc.) |
| cepage | VARCHAR(255) | Grape variety |
| sucrosite_niveau | VARCHAR(50) | Sugar level (Dry, Off-dry, Sweet) |
| price_band | VARCHAR(50) | Price category |
| premium_tier | INTEGER | Tier level for UPSELL (0, 1, 2, 3) |
| aroma_* | INTEGER | 7 aroma axes (1-5 scale) |
| is_active | BOOLEAN | Available for recommendations |
| season_tags | JSON | ["summer", "christmas", ...] |
| global_popularity_score | FLOAT | Popularity for WINBACK |

### Customer Table

| Column | Type | Notes |
|--------|------|-------|
| customer_code | VARCHAR(255) | Primary key |
| email | VARCHAR(512) | Contact email (nullable) |
| is_contactable | BOOLEAN | Can be contacted |
| is_bounced | BOOLEAN | Email bounced |
| is_optout | BOOLEAN | Opted out |
| batch_id | VARCHAR(255) | Source import batch |

### OrderLine Table

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT | Primary key |
| customer_code | VARCHAR(255) | FK to customer |
| product_key | VARCHAR(255) | FK to product |
| order_date | DATE | Purchase date |
| doc_ref | VARCHAR(255) | Invoice/order reference |
| amount_ht | FLOAT | Amount excluding tax |
| amount_ttc | FLOAT | Amount including tax |

### ClientMasterProfile Table

Consolidated customer features:

| Feature | Columns |
|---------|----------|
| RFM | recence_jours, nb_commandes, ca_ht, r_score, f_score, m_score, rfm, segment |
| Top Families | top_family_1, top_family_1_ca_share, top_family_2, ... |
| Top Grapes | top_grape_1, top_grape_1_ca_share, top_grape_2, ... |
| Top Sugar | top_sugar_1, top_sugar_1_ca_share, top_sugar_2, ... |
| Top Budget | top_budget_1, top_budget_1_ca_share, top_budget_2, ... |
| Aroma | aroma_axe_1, aroma_score_1, aroma_axe_2, aroma_confidence, aroma_level |

### RecoItem Table

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT | Primary key |
| run_id | VARCHAR(255) | FK to reco_run |
| customer_code | VARCHAR(255) | FK to customer |
| scenario | VARCHAR(50) | REBUY, CROSS_SELL, UPSELL, WINBACK, NURTURE |
| rank | INTEGER | 1, 2, or 3 |
| product_key | VARCHAR(255) | FK to product |
| score | FLOAT | Recommendation score |
| reasons_json | JSON | Score breakdown {"family_match": 0.8, ...} |

## Indexing Strategy

Key indexes for performance:

```sql
-- Lookup queries
CREATE INDEX ix_customer_email ON customer(email);
CREATE INDEX ix_product_family ON product(family_crm);

-- Time-range queries
CREATE INDEX ix_orderline_customer_date ON order_line(customer_code, order_date);
CREATE INDEX ix_contact_customer_date ON contact_event(customer_code, contact_date);

-- Run queries
CREATE INDEX ix_reco_run_customer ON reco_item(run_id, customer_code);
CREATE INDEX ix_audit_run_customer ON audit_item(run_id, customer_code);
```

## Common Operations

### Check Database Connection

```bash
# Using Docker
docker compose exec db psql -U postgres -d crm_reco_platform -c "SELECT version();"

# Direct connection
psql -U postgres -h localhost -d crm_reco_platform_dev
```

### View Table Sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Backup Database

```bash
# Full backup
pg_dump -U postgres crm_reco_platform_dev > backup_$(date +%Y%m%d_%H%M%S).sql

# With Docker
docker compose exec db pg_dump -U postgres crm_reco_platform > backup.sql
```

### Restore Database

```bash
# Restore from backup
psql -U postgres crm_reco_platform_dev < backup.sql

# With Docker
docker compose exec -T db psql -U postgres crm_reco_platform < backup.sql
```

## Troubleshooting

### Connection Issues

```bash
# Check if postgres is running
docker compose ps db

# Check logs
docker compose logs db

# Restart
docker compose restart db
```

### Migration Issues

```bash
# Show alembic version
alembic current

# See pending migrations
alembic upgrade head --sql

# Rollback and retry
alembic downgrade -1
alembic upgrade head
```

### Stale Connection Pool

If connections hang, restart:

```bash
docker compose down
docker compose up -d db
python scripts/init_db.py --init
```

## Development Workflow

1. **Modify Models** in `core/db/models.py`
2. **Generate Migration**:
   ```bash
   alembic revision --autogenerate -m "Describe change"
   ```
3. **Review Migration** in `alembic/versions/`
4. **Apply Migration**:
   ```bash
   alembic upgrade head
   ```
5. **Test Changes** in your code
6. **Commit Migration** to Git

## Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
