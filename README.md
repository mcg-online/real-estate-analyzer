# Real Estate Investment Analysis Tool

A comprehensive web application for analyzing residential real estate investment opportunities. This tool helps investors identify profitable properties through detailed financial analysis, tax benefit calculations, financing comparisons, and geographic market insights.

## Features

### Property Analysis
- Calculate ROI, cap rate, cash-on-cash return, and monthly cash flow
- Estimate tax benefits including depreciation and deductions
- Compare conventional, FHA, and VA loan options
- Score properties on a 0-100 scale based on comprehensive investment metrics
- Risk assessment across market, vacancy, property condition, and financing dimensions

### Market Analysis
- Analyze investment potential across states, cities, and zip codes
- Identify top-performing markets based on ROI and other metrics
- View market-specific tax incentives and financing programs

### User Interface
- Interactive maps for visualizing property locations (Leaflet)
- Customizable filters to find properties matching your criteria
- Comprehensive property detail views with tabbed analysis
- Dynamic charts for comparing investment metrics (Chart.js)

## Tech Stack

- **Frontend**: React.js, Tailwind CSS, Chart.js, Leaflet
- **Backend**: Python, Flask, Flask-RESTful
- **Database**: MongoDB
- **Auth**: JWT (Flask-JWT-Extended)
- **Deployment**: Docker, Docker Compose

## Architecture

```
real-estate-analyzer/
├── backend/
│   ├── app.py                  # Flask app entry point
│   ├── models/
│   │   └── property.py         # Property model (MongoDB)
│   ├── routes/
│   │   ├── properties.py       # CRUD endpoints
│   │   ├── analysis.py         # Analysis endpoints
│   │   └── users.py            # Auth endpoints
│   ├── services/
│   │   ├── analysis/
│   │   │   ├── financial_metrics.py    # ROI, cap rate, cash flow
│   │   │   ├── opportunity_scoring.py  # 0-100 investment scoring
│   │   │   ├── risk_assessment.py      # Risk evaluation
│   │   │   ├── tax_benefits.py         # Tax deduction analysis
│   │   │   └── financing_options.py    # Loan comparisons
│   │   ├── data_collection/
│   │   │   ├── zillow_scraper.py
│   │   │   └── data_collection_service.py
│   │   └── scheduler.py        # Background data updates
│   ├── utils/
│   │   └── database.py         # MongoDB connection
│   └── tests/                  # pytest test suite
├── frontend/
│   ├── src/
│   │   ├── App.js              # Router & layout
│   │   ├── components/         # React components
│   │   └── services/api.js     # API client
│   └── package.json
├── docker-compose.yml
├── requirements.txt
└── .env
```

## API Endpoints

### Properties
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/properties` | List properties (supports filtering, pagination, sorting) |
| POST | `/api/properties` | Create a new property |
| GET | `/api/properties/<id>` | Get property by ID |
| PUT | `/api/properties/<id>` | Update a property |
| DELETE | `/api/properties/<id>` | Delete a property |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analysis/property/<id>` | Full property analysis (financial, tax, financing) |
| POST | `/api/analysis/property/<id>` | Custom analysis with user parameters |
| GET | `/api/analysis/market/<id>` | Market analysis |
| GET | `/api/markets/top` | Top markets by ROI |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (returns JWT) |
| POST | `/api/auth/logout` | Logout (requires JWT) |

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 14+
- MongoDB (or use Docker)
- Git

### Using Docker (Recommended)

```bash
git clone https://github.com/yourusername/real-estate-analyzer.git
cd real-estate-analyzer

# Configure environment variables
cp .env .env.local
# Edit .env with your API keys and settings

# Start all services (MongoDB, backend, frontend)
docker-compose up -d
```

Access the application at http://localhost:3000

### Manual Installation

```bash
# Clone
git clone https://github.com/yourusername/real-estate-analyzer.git
cd real-estate-analyzer

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ../requirements.txt

# Frontend
cd ../frontend
npm install

# Start MongoDB (must be running on localhost:27017)

# Start backend
cd ../backend
python app.py

# Start frontend (separate terminal)
cd ../frontend
npm start
```

Access the application at http://localhost:3000

### Running Tests

```bash
cd backend
pytest tests/ -v
```

## Configuration

Environment variables (`.env`):

```
DATABASE_URL=mongodb://localhost:27017/realestate
API_KEY_ZILLOW=your_zillow_api_key
JWT_SECRET=your_secret_key
REACT_APP_API_URL=http://localhost:5000/api
```

## License

This project is licensed under the MIT License.
