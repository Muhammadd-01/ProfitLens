# ProfitLens

**Turn Business Data Into Profitable Decisions.**

AI-Powered Business Intelligence & Predictive Analytics SaaS for small and medium-sized businesses.

## What is ProfitLens?

ProfitLens is a data science decision-support platform that allows business owners to upload their business data and automatically receive:

- 📊 **Sales Insights** — Revenue trends, product performance, KPIs
- 👥 **Customer Segmentation** — RFM analysis + K-Means clustering
- ⚠️ **Churn Prediction** — Identify at-risk customers before they leave
- 📈 **Sales Forecasting** — Predict future revenue with confidence intervals
- 🔍 **Anomaly Detection** — Flag unusual transactions automatically
- 💬 **Review Analysis** — Sentiment classification from customer feedback
- 📋 **Business Reports** — Professional exportable reports

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| Backend | Python + FastAPI |
| Data Science | Pandas + NumPy + Scikit-learn + Statsmodels |
| Database | MongoDB & MongoDB Compass (Native Motor async driver) |
| Charts | Recharts + Plotly |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- MongoDB & MongoDB Compass (running locally on `mongodb://localhost:27017`)

### Installation & Quickstart

```bash
# Clone the repository
git clone <repo-url>
cd profitlens

# Copy environment variables
cp .env.example .env
# Default connects to mongodb://localhost:27017 with database 'profitlens'

# Install all dependencies (backend venv + frontend npm)
make install

# Seed MongoDB with synthetic retail dataset (viewable immediately in Compass)
make seed-db

# Start backend server (terminal 1)
make backend

# Start frontend server (terminal 2)
make frontend
```

The app will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Interactive Docs: http://localhost:8000/api/docs
- MongoDB Compass: Connect to `mongodb://localhost:27017` -> database `profitlens`

**Default Credentials:**
- Email: `demo@profitlens.ai`
- Password: `password123`

### Project Structure

```
profitlens/
├── frontend/          # React + TypeScript + Vite
├── backend/           # FastAPI + Data Science
│   ├── app/
│   │   ├── api/       # API route handlers
│   │   ├── models/    # MongoDB Document models & schemas
│   │   ├── schemas/   # Pydantic request/response schemas
│   │   ├── services/  # Analytics, ML, NLP & Reporting services
│   │   └── utils/     # Shared file and statistical utilities
├── data/
│   ├── seed_mongodb.py # MongoDB database seeding script
│   └── synthetic/     # Generated sample datasets (10k customers, 50k orders)
├── tests/             # Comprehensive pytest backend test suite
└── docs/              # Documentation
```

## Data Science Safety

ProfitLens is an analytical decision-support tool. It:

- ✅ Clearly communicates uncertainty in all predictions
- ✅ Distinguishes between data-driven findings and suggestions
- ✅ Shows confidence levels and model evaluation metrics
- ✅ Explains the methodology behind every analysis
- ❌ Never claims predictions are guaranteed
- ❌ Never fabricates insights without supporting data

## License

Proprietary — All rights reserved.
