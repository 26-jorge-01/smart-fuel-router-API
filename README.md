# 🚚 Smart Fuel Router API

[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green?style=flat-square&logo=django)](https://www.djangoproject.com/)
[![PostGIS](https://img.shields.io/badge/PostGIS-Enabled-blue?style=flat-square&logo=postgresql)](https://postgis.net/)
[![Redis](https://img.shields.io/badge/Redis-Caching-red?style=flat-square&logo=redis)](https://redis.io/)

A high-performance, professional-grade API designed to optimize fuel stops for long-haul logistics in the United States. This project demonstrates complex algorithm implementation (Greedy Optimization), multi-provider geocoding strategies, and scalable system architecture.

---

## 🚀 Key Features

- **Optimal Fuel Planning**: Uses a customized Greedy Algorithm to find the cheapest fuel stops without risking range exhaustion.
- **Smart Geocoding Router**: A resilient geocoding layer that intelligently switches between **Google Maps**, **US Census Bureau**, and **OpenStreetMap (Nominatim)** based on query type and availability.
- **High-Performance Spatial Search**: Leverages **PostGIS** `ST_DWithin` and GIST indexing for sub-second corridor searches along thousand-mile routes.
- **Enterprise Ready**: Full Docker orchestration, professional testing suite, and Redis-backed performance caching.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, Django, Django REST Framework.
- **Database**: PostgreSQL with PostGIS extensions.
- **Navigation**: OSRM (Open Source Routing Machine).
- **Caching**: Redis.
- **Infrastructure**: Docker & Docker Compose.

---

## 📖 Documentation

We provide comprehensive guides for both developers and API consumers:

- 🏗️ **[Technical Architecture](docs/architecture.md)**: Deep dive into the algorithms, geocoding logic, and "why" behind the engineering decisions.
- 🔌 **[API Consumer Guide](docs/api_guide.md)**: Quick-start guide for integrating the API into your applications.
- ✅ **[Validation Guide](validation_guide.md)**: Step-by-step instructions for verifying system correctness.

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
