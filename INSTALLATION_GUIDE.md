# 📄 Installation & Usage Guide

**Platform**: Wine Recommendation CRM  
**Version**: 1.0.0  
**Updated**: 26 December 2025

---

## 📦 Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows
- **Python**: 3.9+
- **Database**: SQLite (default) or PostgreSQL (production)
- **Memory**: 2GB minimum
- **Disk**: 1GB for code + dependencies

### Tools Required
```bash
# Python
python --version  # 3.9+
pip --version     # Latest

# Git
git --version     # Latest

# Database (optional for PostgreSQL)
psql --version    # Latest
```

---

## 🚀 Quick Start (5 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/Slyven-test/crm-reco-platform.git
cd crm-reco-platform
```

### 2. Create Virtual Environment
```bash
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Database
```bash
# Create SQLite database
python scripts/setup_db.py

# Or with PostgreSQL (see Configuration section)
export DATABASE_URL=postgresql://user:password@localhost:5432/recommendations
alembic upgrade head
```

### 5. Run API Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Access API
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

✅ **You're ready to go!**

---

## 📁 Step-by-Step Installation

### Step 1: Clone Repository
```bash
# SSH (recommended if you have SSH key configured)
git clone git@github.com:Slyven-test/crm-reco-platform.git

# HTTPS
git clone https://github.com/Slyven-test/crm-reco-platform.git

# Navigate to directory
cd crm-reco-platform
```

### Step 2: Setup Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/macOS:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# Windows (CMD):
venv\Scripts\activate.bat

# Verify activation (you should see (venv) in prompt)
which python  # Linux/macOS
where python  # Windows
```

### Step 3: Install Python Packages
```bash
# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "fastapi|sqlalchemy|pydantic"
```

### Step 4: Configure Database

#### Option A: SQLite (Development)
```bash
# Create database file
sqlite3 recommendations.db < schema.sql

# Or use Python script
python scripts/setup_db.py

# Verify
sqlite3 recommendations.db ".tables"
```

#### Option B: PostgreSQL (Production)
```bash
# Install PostgreSQL (if needed)
# Linux: sudo apt-get install postgresql
# macOS: brew install postgresql
# Windows: https://www.postgresql.org/download/windows/

# Start PostgreSQL service
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS

# Create database
creatdb recommendations
psql recommendations < schema.sql

# Set environment variable
export DATABASE_URL=postgresql://user:password@localhost:5432/recommendations

# Or create .env file
echo "DATABASE_URL=postgresql://user:password@localhost:5432/recommendations" > .env
```

### Step 5: Run Application

#### Development
```bash
# With auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# With specific settings
uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --reload \
  --log-level debug
```

#### Production
```bash
# With Gunicorn
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info

# With Systemd (Linux)
# Create /etc/systemd/system/recommendation-api.service
[Unit]
Description=Wine Recommendation API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/app
Environment="PATH=/app/venv/bin"
ExecStart=/app/venv/bin/gunicorn api.main:app --workers 4
Restart=always

[Install]
WantedBy=multi-user.target

# Then:
sudo systemctl enable recommendation-api
sudo systemctl start recommendation-api
```

---

## 👋 Usage

### Loading Data

#### 1. Prepare CSV Files
```
data/
├── customers.csv
├── sales_lines.csv
├── contact_events.csv
└── products.csv
```

#### 2. Load Data
```python
from core.ingestion import DataIngestionOrchestrator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Setup
engine = create_engine('sqlite:///recommendations.db')
db = Session(engine)

# Load CSV files
orchestrator = DataIngestionOrchestrator(db)
status, success = orchestrator.run_full_pipeline(
    ingestion_batch_id='550e8400-e29b-41d4-a716-446655440000',
    csv_directory='data/',
)

print(f"Ingested: {status.customers_ingested} customers")
print(f"Success: {success}")
```

Or via command line:
```bash
cd scripts
python load_data.py --csv-dir ../data/ --batch-id 550e8400-e29b-41d4-a716-446655440000
```

### Transform & Clean Data

```python
from core.transform import TransformOrchestrator

# Setup
engine = create_engine('sqlite:///recommendations.db')
db = Session(engine)

# Run transformation
orchestrator = TransformOrchestrator(db)
status, success = orchestrator.run_full_pipeline(
    ingestion_batch_id='550e8400-e29b-41d4-a716-446655440000'
)

print(f"Customers processed: {status.customers_loaded}")
print(f"Orders processed: {status.order_lines_loaded}")
```

### Generate Recommendations

```python
from core.recommendation import RecommendationEngine
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Setup
engine = create_engine('sqlite:///recommendations.db')
db = Session(engine)

# Generate single customer
engine = RecommendationEngine(db)
result, success = engine.generate_recommendations(
    customer_code='C001',
    max_recommendations=3,
)

if success:
    for reco in result.recommendations:
        print(f"{reco.rank}. {reco.product_key}")
        print(f"   Scenario: {reco.scenario}")
        print(f"   Score: {reco.score.final_score:.1f}")

# Generate batch
results = engine.generate_batch_recommendations(
    limit=1000  # Process 1000 customers
)
print(f"Success: {sum(1 for _, s in results.values() if s)}/{len(results)}")
```

### Use REST API

#### Get Recommendations
```bash
curl -X GET "http://localhost:8000/api/v1/recommendations/C001?max_recommendations=5"
```

#### Filter by Scenario
```bash
curl -X GET "http://localhost:8000/api/v1/recommendations/C001/filtered?scenario=UPSELL&min_score=75"
```

#### Get History
```bash
curl -X GET "http://localhost:8000/api/v1/recommendations/C001/history"
```

#### Get Statistics
```bash
curl -X GET "http://localhost:8000/api/v1/recommendations/stats/overview?from_date=2025-12-01&to_date=2025-12-31"
```

#### Batch Process
```bash
curl -X POST "http://localhost:8000/api/v1/recommendations/batch" \
  -H "Content-Type: application/json" \
  -d '{"customer_codes": null, "limit": 100, "save_results": true}'
```

#### Delete Recommendations
```bash
# Delete specific customer
curl -X DELETE "http://localhost:8000/api/v1/recommendations/C001"

# Delete old (30+ days)
curl -X DELETE "http://localhost:8000/api/v1/recommendations/all/old?days_old=30"
```

---

## 👊 Using Python Client

```python
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

# 1. Get recommendations
response = requests.get(
    f"{BASE_URL}/recommendations/C001",
    params={"max_recommendations": 5}
)
recos = response.json()

print(f"Generated {len(recos['recommendations'])} recommendations")
for reco in recos['recommendations']:
    print(f"  {reco['rank']}. {reco['product_key']}")
    print(f"     {reco['explanation']['reason']}")

# 2. Filter by scenario
response = requests.get(
    f"{BASE_URL}/recommendations/C001/filtered",
    params={
        "scenario": "UPSELL",
        "min_score": 75
    }
)
filtered = response.json()

# 3. Get history
response = requests.get(
    f"{BASE_URL}/recommendations/C001/history"
)
history = response.json()
print(f"Found {len(history['history'])} historical runs")

# 4. Get statistics
response = requests.get(
    f"{BASE_URL}/recommendations/stats/overview",
    params={
        "from_date": "2025-12-01",
        "to_date": "2025-12-31"
    }
)
stats = response.json()
print(f"Total recommendations: {stats['total_recommendations']}")
print(f"Unique customers: {stats['unique_customers']}")
print(f"Average score: {stats['avg_score']:.1f}")

# 5. Batch generate
response = requests.post(
    f"{BASE_URL}/recommendations/batch",
    json={
        "customer_codes": None,
        "limit": 1000,
        "save_results": True
    }
)
batch = response.json()
print(f"Batch: {batch['successful']}/{batch['total']} successful")
print(f"Duration: {batch['duration_seconds']:.1f}s")
```

---

## 🗪 Testing

### Run All Tests
```bash
pytest -v
```

### Run Specific Module
```bash
# Test recommendations
pytest tests/test_recommendation.py -v

# Test API
pytest tests/test_api.py -v

# Test transformations
pytest tests/test_transform.py -v
```

### With Coverage
```bash
pytest --cov=core --cov=api --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Run Specific Test
```bash
pytest tests/test_recommendation.py::TestFeatureComputer::test_compute_customer_features -v
```

---

## ⚙️ Configuration

### Environment Variables
Create `.env` file in project root:

```bash
# Database
DATABASE_URL=sqlite:///recommendations.db
# Or PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/recommendations

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature Flags
ENABLE_SILENCE_CHECK=true
SILENCE_WINDOW_DAYS=30
MAX_RECOMMENDATIONS=10
```

### Load .env File
```python
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
```

---

## 📈 Monitoring

### Check API Health
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
# API logs
journalctl -u recommendation-api -f  # With Systemd

# Or from stdout if running in terminal
```

### Monitor Database
```bash
# SQLite
sqlite3 recommendations.db "SELECT COUNT(*) FROM reco_item;"

# PostgreSQL
psql recommendations -c "SELECT COUNT(*) FROM reco_item;"
```

---

## 🚠 Troubleshooting

### Port Already in Use
```bash
# Use different port
uvicorn api.main:app --port 8001

# Or kill process using port 8000
# Linux/macOS:
lsof -ti:8000 | xargs kill -9

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database Connection Error
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
python -c "from sqlalchemy import create_engine; engine = create_engine('sqlite:///recommendations.db'); print('OK')"
```

### Import Errors
```bash
# Reinstall dependencies
pip install --upgrade --force-reinstall -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### API Not Responding
```bash
# Check if running
curl http://localhost:8000/health

# View logs
uvicorn api.main:app --log-level debug
```

---

## 📄 File Reference

**Documentation**:
- `PROJECT_STATUS.md` - Project status & roadmap
- `INSTALLATION_GUIDE.md` - This file
- `docs/STEP_*.md` - Detailed step documentation
- `docs/API.md` - API documentation

**Code**:
- `core/` - Core modules
- `api/` - REST API
- `tests/` - Test suite
- `scripts/` - Utility scripts

**Configuration**:
- `requirements.txt` - Python dependencies
- `schema.sql` - Database schema
- `.env.example` - Environment variables template

---

## 📧 Support

**Documentation**: `/docs` folder  
**API Docs**: http://localhost:8000/api/docs  
**Source Code**: [GitHub](https://github.com/Slyven-test/crm-reco-platform)  

---

**✅ Installation Complete!**

Next: Follow the usage examples above to generate recommendations.
