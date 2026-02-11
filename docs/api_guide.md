# API Consumer Guide

Welcome to the Fuel Routing API. This guide will help you integrate and consume the API for your logistics or navigation applications.

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

## Interactive Documentation
A live Swagger UI is available at:
[http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

Here you can test the API directly from your browser and view the full OpenAPI schema.

## Error Handling
The API uses standard HTTP status codes:
- `200`: Success.
- `400`: Bad Request (Invalid parameters or geocoding failure).
- `500`: Internal Server Error.
