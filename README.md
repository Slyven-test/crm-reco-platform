# CRM & Product Recommendation Platform for Offline Winery Sales

**Build Guide v1.4** - Production-grade blueprint for intelligent product recommendations with audit-first approach.

## 📋 Project Overview

This platform ingests customer and sales data exports (iSaVigne/iSaCompta), builds enriched customer profiles (RFM + preferences + aroma), and generates 2-3 safe product recommendations with business logic guardrails and comprehensive audit trails.

### Key Features
- **Smart Customer Segmentation**: RFM analysis + taste preferences + aroma profiles
- **Scenario-Based Recommendations**: REBUY, CROSS_SELL, UPSELL, WINBACK, NURTURE
- **Audit-First Architecture**: Every recommendation passes strict guardrails before export
- **Deterministic Outputs**: Same inputs + config = same results (reproducible)
- **Admin Dashboard**: Streamlit UI for management and monitoring

## 🚀 Quick Start (Development)

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker + docker-compose (Linux)
- Python 3.11+ (for local development)
- Git

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Slyven-test/crm-reco-platform.git
cd crm-reco-platform

# 2. Copy environment file
cp .env.example .env

# 3. Start containers
docker compose up -d db
docker compose up -d redis

# 4. Run migrations
docker compose exec api alembic upgrade head

# 5. Start API and Admin UI
docker compose up api admin
```

**Access Points:**
- API: http://localhost:8000
- Admin UI: http://localhost:8501
- Database: localhost:5432

## 📁 Project Structure

```
crm-reco-platform/
├── apps/
│   ├── api/                    # FastAPI application
│   │   └── main.py
│   └── admin_ui/               # Streamlit admin dashboard
│       └── app.py
├── core/
│   ├── config/                 # YAML configs + schema validation
│   ├── db/                     # SQLAlchemy models + migrations
│   ├── ingestion/              # CSV import + validation + normalization
│   ├── features/               # RFM, preferences, aroma computation
│   ├── recommender/            # Scenario selection + scoring + diversity
│   ├── audit/                  # Audit rules + gating
│   ├── export/                 # CSV export builders
│   ├── security/               # Auth, roles, secrets
│   └── utils/                  # Logging, helpers
├── tests/                      # Unit + integration tests
├── docker/                     # Docker configuration
├── docs/                       # Documentation
├── data/
│   ├── inbox/                  # Drop CSV exports here
│   ├── exports/                # Generated outputs
│   └── backups/                # Database backups
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 📊 Data Flow

1. **Drop Exports** → CSV files in `data/inbox/`
2. **Ingest & Validate** → Read, normalize, detect errors
3. **Build Features** → RFM, preferences, aroma profiles
4. **Choose Scenario** → REBUY, CROSS_SELL, UPSELL, WINBACK, HOLD
5. **Generate Candidates** → Filtered product set per scenario
6. **Score & Rank** → Personalized scoring with weights
7. **Diversity Check** → Remove repetitive combinations
8. **Audit & Gate** → Apply business rules, generate flags
9. **Export Results** → CSV files for campaigns

## 🎯 Success Metrics (v1.4)

- ✅ Weekly run time: **< 10 minutes** manual work
- ✅ Exported customers with audit ERROR: **0%**
- ✅ Customers with audit_score >= 80: **>= 80%**
- ✅ Spot-check quality (20 random customers): **< 2 feel wrong**
- ✅ Measurable reactivation uplift within 2-3 months

## 🛠 Tech Stack

- **Backend**: Python 3.11+ + FastAPI
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Admin UI**: Streamlit
- **Containerization**: Docker + docker-compose
- **CI/CD**: GitHub Actions

## 📚 Documentation

See [Build Guide v1.4](./docs/BUILD_GUIDE_v1.4.md) for:
- Detailed module specifications
- Data model and schema
- Configuration examples (YAML)
- SQL DDL skeletons
- Troubleshooting checklist

## 🔐 Security & Privacy

- Environment-based secrets (never in Git)
- PostgreSQL user authentication
- RGPD compliance ready
- Role-based access control (Admin, Marketing, Read-only)
- Audit trails on all operations

## 📝 Implementation Roadmap

1. ✅ Database models + migrations
2. ✅ Ingestion module (CSV readers + validators)
3. ✅ Normalization pipeline
4. ⏳ Feature engineering (RFM + preferences + aroma)
5. ⏳ Scenario selection
6. ⏳ Recommendation engine
7. ⏳ Audit + gating
8. ⏳ Admin UI
9. ⏳ Outcomes loop
10. ⏳ CI/CD pipelines

## 🤝 Contributing

Each module is built step-by-step:
- Code + tests + fixtures + documentation per module
- Deliverables always include: code, tests, docs
- No hardcoded values (YAML config only)
- Deterministic outputs validated via golden tests

## 📞 Support

For issues or questions:
1. Check [Troubleshooting](./docs/TROUBLESHOOTING.md)
2. Review [Build Guide examples](./docs/BUILD_GUIDE_v1.4.md#appendix-c---troubleshooting-checklist)
3. Open a GitHub issue

---

**Last Updated**: 2025-12-26
**Version**: v1.4 (Development)
