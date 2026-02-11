# API Consumer Guide

Welcome to the Fuel Routing API. This guide will help you integrate and consume the API for your logistics or navigation applications.

## Authentication

This API requires an API Key for all requests. The key must be sent in the `X-API-Key` header.

**Header**: `X-API-Key: <your_api_key>`

---

## Endpoints

### Post `api/v1/route-plan/`
Plan an optimal trip with fuel stops.

**Request Body (JSON)**:
| Field | Type | Description |
| :--- | :--- | :--- |
| `start` | String | Start location (Address or City, State) |
| `finish` | String | Destination location (Address or City, State) |
| `corridor_miles` | Integer | (Optional) Search radius around the route. Default: 10. |

**Example Request**:
```json
{
  "start": "Miami, FL",
  "finish": "Atlanta, GA",
  "corridor_miles": 15
}
```

## Response Format

The response returns a serialized travel plan:

```json
{
  "total_distance_miles": 662.5,
  "total_gallons": 66.25,
  "total_cost": 198.75,
  "fuel_plan": [
    {
      "name": "Flying J #123",
      "address": "123 Highway Ave",
      "gallons_purchased": 50.0,
      "stop_cost": 150.0,
      "price_per_gallon": 3.00,
      "lat": 25.7617,
      "lon": -80.1918
    }
  ],
  "polyline": "encoded_polyline_string_..."
}
```

## 💡 Real-World Scenarios

### Scenario: The NYC to Miami Express
A carrier needs to plan a 1,300-mile route. Without an optimizer, a driver might fill up in NYC (expensive) and halfway through Virginia (expensive). 

**The Optimized Solution**:
Using the API with `corridor_miles: 15`, the system identifies a massive price drop in **South Carolina**. The API instructs the driver to buy only enough fuel to reach SC, and then "Fill Up" at the local minimum before finishing the trip.

---

## Error Handling Philosophy
We believe an API should be **instructive**, not just reactive.

- **Geocoding Failures**: If the API can't find your address, the error message tells you *why* (e.g., "Census API failed and Google Key is missing") and suggests how to fix it.
- **Unreachable Routes**: If the distance between stations exceeds the vehicle range (500 miles), the API returns a `422 Unprocessable Entity` with a list of missing coverage areas.
