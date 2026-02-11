# Validation Guide

This guide describes how to verify that the Fuel Routing API is functioning correctly.

## 1. Automated Tests
Run the full test suite using Pytest inside the Docker container:
```bash
docker compose exec web pytest
```
*Verification*: All tests should pass (green).

## 2. API Responses (Manual)
Use the Swagger UI or Postman to execute a request.

**Swagger UI URL**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

**Test Payload**:
```json
{
  "start": "Miami, FL",
  "finish": "New York, NY",
  "corridor_miles": 10
}
```

**What to verify in the response**:
- **Status Code**: `200 OK`.
- **JSON Body**:
    - `fuel_plan`: Should be a list of stops.
    - `total_gallons`: Should be a float (e.g., `77.87`).
    - `total_cost`: Should be a float (e.g., `225.98`).
    - `polyline`: A long string representing the route.

## 3. Business Logic Validation
- **Sequence**: Check that `miles_from_start` in the `fuel_plan` increases for each stop.
- **Range**: Ensure no gap between stops (or between start/finish and first/last stop) exceeds 500 miles.
- **Cheapest Stop**: Check a few stops against the original CSV data to see if the chosen station is indeed among the cheaper options in its area.

## 4. Geocoding Validation
Try a request with a specific address vs a city:
- **City**: `Miami, FL` (Handled by OSM/Google).
- **Address**: `1600 Pennsylvania Ave NW, Washington, DC` (Handled by Census/Google).

If you receive a `400 Bad Request` with a geocoding error, check if your `GOOGLE_MAPS_API_KEY` is set correctly in `.env`.
