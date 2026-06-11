#!/usr/bin/env python
import json
import sys
import warnings
from datetime import date

from crewai import Crew

from ai_travel_assistant.crew import AiTravelAssistant, TravelRequest

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

SAMPLE_REQUEST = TravelRequest(
    origin="Singapore",
    destinations=["Tokyo", "Osaka"],
    start_date=date(2025, 9, 1),
    end_date=date(2025, 9, 10),
    group_size=2,
    budget_type="mid-range",
    interests=["food", "local culture", "sightseeing"],
    travel_style="relax",
    currency="SGD",
)


def _build_crew() -> Crew:
    return AiTravelAssistant().crew()


def run():
    """
    Run the crew.
    """
    inputs = SAMPLE_REQUEST.to_crew_inputs()

    try:
        _build_crew().kickoff(inputs=inputs)
    except Exception as e:
        raise RuntimeError(f"An error occurred while running the crew: {e}") from e


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = SAMPLE_REQUEST.to_crew_inputs()
    try:
        _build_crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise RuntimeError(f"An error occurred while training the crew: {e}") from e


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        _build_crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise RuntimeError(f"An error occurred while replaying the crew: {e}") from e


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = SAMPLE_REQUEST.to_crew_inputs()

    try:
        _build_crew().test(
            n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise RuntimeError(f"An error occurred while testing the crew: {e}") from e


def run_with_trigger():
    """
    Run the crew with trigger payload.
    Expects a JSON object matching TravelRequest fields as a CLI argument.
    Example: run_with_trigger '{"origin":"Singapore","destinations":["Tokyo"],...}'
    """
    if len(sys.argv) < 2:
        raise ValueError(
            "No trigger payload provided. Please provide JSON payload as argument."
        )

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        raise ValueError("Invalid JSON payload provided as argument") from e

    try:
        request = TravelRequest.model_validate(trigger_payload)
    except Exception as e:
        raise ValueError(f"Invalid TravelRequest payload: {e}") from e

    try:
        return _build_crew().kickoff(inputs=request.to_crew_inputs())
    except Exception as e:
        raise RuntimeError(
            f"An error occurred while running the crew with trigger: {e}"
        ) from e
