"""Trip endpoints: list, create (background task), and an auth smoke-test."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from ai_travel_assistant.crew import TravelRequest
from ai_travel_assistant.flight_flow import FlightRequest
from ai_travel_assistant.hotel_flow import HotelRequest
from api.schemas import TripCreate, TripRead
from api.security import get_current_user
from api.storage import Storage, User, get_storage
from api.tasks import run_trip

router = APIRouter(prefix="/trips", tags=["trips"])

# trip_type -> the domain model that validates its free-form request payload.
_REQUEST_MODELS = {
    "itinerary": TravelRequest,
    "flights": FlightRequest,
    "hotels": HotelRequest,
}

# `request` is a free-form dict (one of three shapes by trip_type), so OpenAPI
# can't infer per-type fields. These labelled examples render as a dropdown in
# Swagger ("Try it out") and document each shape — including the configurable
# guest counts — without changing the contract.
_TRIP_EXAMPLES = {
    "itinerary": {
        "summary": "Itinerary — multi-agent day-by-day plan",
        "value": {
            "trip_type": "itinerary",
            "request": {
                "origin": "Singapore",
                "destinations": ["Tokyo", "Osaka"],
                "start_date": "2026-09-01",
                "end_date": "2026-09-10",
                "group_size": 2,
                "budget_type": "mid-range",
                "interests": ["food", "culture"],
                "travel_style": "relax",
                "currency": "SGD",
            },
        },
    },
    "flights": {
        "summary": "Flights — round-trip search (configurable adults)",
        "value": {
            "trip_type": "flights",
            "request": {
                "origin": "Singapore",
                "destinations": ["Tokyo"],
                "start_date": "2026-08-01",
                "end_date": "2026-08-05",
                "currency": "SGD",
                "adults": 2,
            },
        },
    },
    "hotels": {
        "summary": "Hotels — per-city search (configurable guests)",
        "value": {
            "trip_type": "hotels",
            "request": {
                "destinations": ["Tokyo"],
                "start_date": "2026-08-01",
                "end_date": "2026-08-05",
                "currency": "SGD",
                "adults": 2,
                "children": 1,
            },
        },
    },
}


@router.get("/test")
def trips_test(user: User = Depends(get_current_user)) -> dict:
    """Smoke-test that the trips router requires a valid JWT."""
    return {"message": f"Authenticated as {user.email}"}


@router.get("", response_model=list[TripRead])
def list_trips(
    user: User = Depends(get_current_user),
    storage: Storage = Depends(get_storage),
) -> list[TripRead]:
    """Return all trips owned by the authenticated user."""
    return storage.list_trips(user.id)


@router.post("", response_model=TripRead, status_code=status.HTTP_202_ACCEPTED)
def create_trip(
    body: Annotated[TripCreate, Body(openapi_examples=_TRIP_EXAMPLES)],
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    storage: Storage = Depends(get_storage),
) -> TripRead:
    """Create a trip and run it in the background.

    The `request` body varies by `trip_type` — see the example dropdown:
    - **itinerary** → `TravelRequest` (origin, destinations, dates, group_size,
      budget_type, interests, travel_style, currency).
    - **flights** → `FlightRequest` (origin, destinations, dates, currency,
      `adults`).
    - **hotels** → `HotelRequest` (destinations, dates, currency, `adults`,
      `children`).

    Returns 202 with the trip in `pending`; poll `GET /trips` for the result.
    """
    model_cls = _REQUEST_MODELS[body.trip_type]
    try:
        validated = model_cls(**body.request)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(exc.errors()),
        )

    trip = storage.create_trip(
        user_id=user.id,
        trip_type=body.trip_type,
        request=validated.model_dump(mode="json"),
    )
    background_tasks.add_task(run_trip, trip.id)
    return trip
