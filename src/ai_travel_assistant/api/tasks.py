"""Background trip runner — executes the crewAI itinerary crew or flight flow.

Mirrors the helpers in ``app.py`` (run_itinerary / run_flight_search). The crewAI
imports are deferred into the runner functions so the API starts fast and auth-only
usage doesn't require the LLM stack to import.

A module-level lock serializes every kickoff: it prevents two runs from
interleaving writes to the shared ``outputs/*.md`` files and ensures only one
run hits the Groq rate limit (``max_rpm=5`` in crew.py) at a time. Valid for a
single worker process only.
"""

import os
import threading
from datetime import datetime, timezone

from ai_travel_assistant.api.storage import get_storage
from ai_travel_assistant.config import (
    FLIGHT_OPTIONS_FILE,
    INSIGHTS_FILE,
    ITINERARY_FILE,
    ensure_outputs_dir,
)
from ai_travel_assistant.crew import AiTravelAssistant, TravelRequest
from ai_travel_assistant.flight_flow import FlightRequest, FlightSearchFlow

_kickoff_lock = threading.Lock()


def _read_output(path: str) -> str | None:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def _run_itinerary(request: dict) -> dict:
    ensure_outputs_dir()
    AiTravelAssistant().crew().kickoff(inputs=TravelRequest(**request).to_crew_inputs())
    return {
        "insights_md": _read_output(INSIGHTS_FILE),
        "itinerary_md": _read_output(ITINERARY_FILE),
    }


def _run_flights(request: dict) -> dict:
    ensure_outputs_dir()
    FlightSearchFlow().kickoff(inputs=FlightRequest(**request).to_flow_inputs())
    return {"flights_md": _read_output(FLIGHT_OPTIONS_FILE)}


def _execute(trip_type: str, request: dict) -> dict:
    if trip_type == "itinerary":
        return _run_itinerary(request)
    if trip_type == "flights":
        return _run_flights(request)
    raise ValueError(f"Unknown trip_type: {trip_type!r}")


def run_trip(trip_id: int) -> None:
    """Run one trip to completion, updating its status/result in storage."""
    storage = get_storage()
    try:
        trip = storage.get_trip(trip_id)
        if trip is None:
            return
        with _kickoff_lock:  # queued trips stay "pending" until they acquire the lock
            storage.update_trip(trip_id, status="running")
            result = _execute(trip.trip_type, trip.request)
        storage.update_trip(
            trip_id,
            status="completed",
            result=result,
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as exc:  # noqa: BLE001 — any failure marks the trip failed
        storage.update_trip(
            trip_id,
            status="failed",
            result={"error": str(exc)},
            completed_at=datetime.now(timezone.utc),
        )
