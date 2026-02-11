# 🚚 Smart Fuel Router: A Logistics Optimization Case Study

[![CI](https://github.com/your-username/spotter/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/spotter/actions)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green?style=flat-square&logo=django)](https://www.djangoproject.com/)
[![PostGIS](https://img.shields.io/badge/PostGIS-Enabled-blue?style=flat-square&logo=postgresql)](https://postgis.net/)

## 📈 The Business Problem
In the long-haul trucking industry, fuel accounts for nearly **30-40% of total operating costs**. A fleet traveling from Miami to New York (approx. 1,300 miles) can see price fluctuations of over **$0.50 per gallon** across state lines. 

**This project solves three critical business questions:**
1.  **Cost Optimization**: *Where should a driver stop to ensure they always pay the lowest possible price without risking fuel exhaustion?*
2.  **Operational Efficiency**: *How can we automate the route planning process while handling "dirty" legacy data from hundreds of different fuel providers?*
3.  **Data Resilience**: *How do we maintain high-accuracy geocoding (finding stations on remote highways) while minimizing expensive API costs?*

---

## 🏗️ The Engineering Challenge
Building a fuel optimizer isn't just about finding the cheapest station; it's about navigating the trade-offs between **graph theory** (route planning), **spatial indexing** (corridor search), and **resource management** (API safety).

### Core Technical Pillars
- **[Algorithm Choice]**: Implemented a modified **Greedy Optimization** algorithm to handle real-time fuel decisions.
- **[Smart Geocoding]**: Created a resilient, multi-tier geocoding router that solves the "highway intersection" problem.
- **[Spatial Intelligence]**: Leverages **PostGIS** for high-performance geometric queries along complex route lines.

---

## 📖 Case Study Documentation
For a deep dive into the engineering and product decisions, explore:

- 🏗️ **[Technical Architecture Deep Dive](docs/architecture.md)**: Diagrams, design patterns, and algorithmic trade-offs (Greedy vs. DP).
- 🔌 **[API Consumer Guide](docs/api_guide.md)**: Real-world use cases and integration instructions.
- 🚀 **[Product Vision](docs/vision.md)**: The "Next Step" roadmap—from MVP to Enterprise scale.

---

## 🚦 Quick Start

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### 2. Launch the Environment
```bash
docker compose up --build
```

### 3. Initialize & Populate
```bash
# Run migrations
docker compose exec web python manage.py migrate

# Import 500+ US fuel stations from CSV
docker compose exec web python manage.py import_fuel_prices --csv data/fuel-prices-for-be-assessment.csv
```

### 4. Test the API
```bash
curl -X POST http://localhost:8000/api/v1/route-plan/ \
  -H "Content-Type: application/json" \
  -d '{
    "start": "Miami, FL",
    "finish": "Atlanta, GA",
    "corridor_miles": 10
  }'
```

---

## 🧪 Testing

The project maintains a high standard of quality through extensive unit and integration tests.

```bash
docker compose exec web pytest tests/
```

---

## ⚙️ Configuration

To unlock high-accuracy highway geocoding, add your Google Maps API key to the `.env` file:
```env
GOOGLE_MAPS_API_KEY=your_api_key_here
```
*Note: The system will automatically fall back to OpenStreetMap and US Census for basic queries if no key is provided.*

---

## 👨‍💻 Author
Developed as a showcase of advanced backend engineering and algorithmic problem-solving.
