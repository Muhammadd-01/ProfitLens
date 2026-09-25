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
| Database | Supabase (managed PostgreSQL) |
| Charts | Recharts + Plotly |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- Supabase account (free tier works)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd profitlens

# Copy environment variables
cp .env.example .env
# Edit .env with your Supabase credentials

# Install all dependencies
make install

# Generate synthetic data for development
make generate-data

# Start backend (terminal 1)
make backend

# Start frontend (terminal 2)
make frontend
```

The app will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

### Project Structure

```
profitlens/
├── frontend/          # React + TypeScript + Vite
├── backend/           # FastAPI + Data Science
│   ├── app/
│   │   ├── api/       # API route handlers
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic request/response schemas
│   │   ├── services/  # Business logic services
│   │   ├── analytics/ # Revenue, customer, product analytics
│   │   ├── ml/        # Machine learning models
│   │   ├── insights/  # Insight generation engine
│   │   └── utils/     # Shared utilities
│   └── alembic/       # Database migrations
├── data/
│   └── synthetic/     # Generated sample data
├── notebooks/         # Jupyter analysis notebook
├── tests/             # Test suites
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
