# JEPCO Grid Stability Orchestrator

**AI-Powered Decision-Support System for Electrical Grid Operations**

An intelligent platform for Jordan Electric Power Company (JEPCO) that predicts transformer overload 24-72 hours in advance and generates automated mitigation plans to prevent power outages.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Overview

The JEPCO Grid Stability Orchestrator is **NOT a chatbot** - it's an operations intelligence platform designed for electrical grid control rooms to:

- **Predict** transformer overload risks 24-72 hours ahead
- **Score** risk using transparent, explainable methodology
- **Simulate** load transfer scenarios to find optimal solutions
- **Generate** AI-enhanced operator instructions with safety checklists
- **Track** field execution through automated work order management
- **Maintain** complete audit trail for regulatory compliance

---

## Key Features

### 1. Baseline Time-Series Forecasting
- Predicts transformer load using historical patterns + seasonality
- 72-hour ahead prediction with confidence scoring
- No black-box ML - transparent statistical approach

### 2. Transparent Risk Scoring
- Weighted formula: 60% overload + 20% thermal + 20% cascading risk
- Human-readable reasons and recommendations
- Risk levels: LOW (0.0-0.3), MEDIUM (0.3-0.7), HIGH (0.7-1.0)

### 3. Mitigation Planning
- Load transfer simulation via topology links
- Finds optimal solutions ranked by risk reduction
- Real-time capacity calculations

### 4. Claude AI Integration
- Generates detailed operator instructions
- Safety-focused prompts with template fallback
- 100% reliability (works without API key)

### 5. Work Order Management
- Auto-incrementing WO numbers (WO-YYYY-####)
- Field checklists and rollback procedures
- Status tracking: OPEN → IN_PROGRESS → COMPLETED

### 6. Complete Audit Trail
- Every action logged for compliance
- User attribution and timestamps
- Regulatory-ready reporting

---

## Tech Stack

- **Backend:** Django 4.2, Django REST Framework
- **Database:** PostgreSQL (production) / SQLite (development)
- **Frontend:** Bootstrap 5, Chart.js
- **AI:** Anthropic Claude Sonnet 4.5 (optional)
- **APIs:** RESTful API with JSON responses

---

## Quick Start

### Prerequisites
- Python 3.11+
- pip and virtualenv
- PostgreSQL (optional for production)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/LailaBalawi/jepco-grid-stability.git
cd jepco-grid-stability
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env and set SECRET_KEY, ANTHROPIC_API_KEY (optional)
```

5. **Setup database:**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Load demo data:**
```bash
python manage.py generate_grid_data
python manage.py generate_load_data
```

7. **Run the server:**
```bash
python manage.py runserver
```

8. **Access the system:**
```
http://localhost:8000
Login: admin / admin123 (demo credentials)
```

---

## Project Structure

```
jepco_grid/
├── config/                 # Django settings and URL routing
├── apps/
│   ├── assets/            # Grid topology (substations, transformers, switches)
│   ├── telemetry/         # Load data collection and storage
│   ├── forecasting/       # Time-series prediction engine
│   ├── risk/              # Risk scoring and assessment
│   ├── planning/          # Mitigation planning simulator
│   ├── llm/               # Claude AI integration
│   └── ops/               # Work orders and audit logs
├── templates/             # HTML templates (Bootstrap 5)
├── static/                # CSS, JavaScript, images
├── requirements.txt       # Python dependencies
└── manage.py              # Django management command
```

---

## System Workflow

```
1. DATA INGESTION
   Load readings from SCADA/sensors → TransformerLoad database

2. FORECASTING
   Predict load 72h ahead → LoadForecast (confidence: 0.60-0.95)

3. RISK ASSESSMENT
   Calculate risk scores → RiskAssessment (HIGH/MEDIUM/LOW)

4. DASHBOARD ALERT
   Display high-risk transformers to operator

5. MITIGATION PLANNING
   Simulate load transfers → Ranked mitigation plans

6. AI ENHANCEMENT
   Claude generates operator instructions + safety checklists

7. OPERATOR APPROVAL
   Human-in-the-loop review and approval

8. WORK ORDER CREATION
   Convert plan to field-executable WO-YYYY-#### format

9. FIELD EXECUTION
   Team follows checklist → Status updates → Completion

10. AUDIT TRAIL
    Every action logged for compliance
```

---

## API Endpoints

### Forecasting
- `POST /api/forecasting/run/` - Run forecasting for all transformers
- `GET /api/forecasting/forecasts/` - List all forecasts

### Risk Assessment
- `POST /api/risk/assess/` - Run risk scoring
- `GET /api/risk/assessments/` - List all risk assessments

### Mitigation Planning
- `POST /api/planning/generate/` - Generate mitigation plans
- `GET /api/planning/plans/` - List all plans

### Work Orders
- `GET /api/ops/workorders/` - List work orders
- `PATCH /api/ops/workorders/{id}/` - Update WO status

---

## Testing

Run end-to-end tests:
```bash
python test_end_to_end.py
```

Run individual component tests:
```bash
python test_forecasting.py
python test_risk_scoring.py
python test_planning.py
python test_llm.py
```

---

## Demo Results

**System Performance (Synthetic Data):**
- 1,680 load readings (7 days × 24h × 10 transformers)
- 21 forecasts generated (10 transformers × 72h)
- 4 HIGH-risk transformers identified
- 7 mitigation plans created
- 79% risk reduction (T-07: 0.737 → 0.154)
- 3 work orders created (WO-2026-0001, 0002, 0003)

**High-Risk Transformers:**
- T-07: 118.2% load, risk 0.737 (CRITICAL)
- T-04: 118.6% load, risk 0.710 (CRITICAL)

---

## Documentation

Full documentation available in:
- `JEPCO_System_Documentation.docx` - Complete user manual
- `JEPCO_System_Documentation.md` - Markdown version
Ask author for documents.
Covers:
- System overview and architecture
- Folder-by-folder explanation
- How to run and deploy
- Website features explained
- Main code locations
- Troubleshooting guide

---

## Author

**Laila Balawi**
- Email: 21210023@htu.edu.jo
- University: AL-Hussien bin Abdullah Technical University

---

**Note:** This is a demonstration system with synthetic data. For production deployment with real SCADA integration, please contact the author.
