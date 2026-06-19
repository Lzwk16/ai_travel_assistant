"""Trip endpoints: list, create (background task), and an auth smoke-test."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from ai_travel_assistant.crew import TravelRequest
from ai_travel_assistant.flight_flow import FlightRequest
from api.schemas import TripCreate, TripRead
from api.security import get_current_user
from api.storage import Storage, User, get_storage
from api.tasks import run_trip

router = APIRouter(prefix="/trips", tags=["trips"])


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
    body: TripCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    storage: Storage = Depends(get_storage),
) -> TripRead:
    """Validate the request payload and enqueue a background trip run."""
    model_cls = TravelRequest if body.trip_type == "itinerary" else FlightRequest
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
