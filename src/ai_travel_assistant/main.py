#!/usr/bin/env python
import sys
import warnings
import json

from datetime import date

from ai_travel_assistant.crew import AiTravelAssistant, TravelRequest

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

sample_request = TravelRequest(
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


def run():
    """
    Run the crew.
    """
    inputs = sample_request.to_crew_inputs()

    try:
        AiTravelAssistant().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = _SAMPLE_REQUEST.to_crew_inputs()
    try:
        AiTravelAssistant().crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        AiTravelAssistant().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = _SAMPLE_REQUEST.to_crew_inputs()

    try:
        AiTravelAssistant().crew().test(
            n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    Expects a JSON object matching TravelRequest fields as a CLI argument.
    Example: run_with_trigger '{"origin":"Singapore","destinations":["Tokyo"],...}'
    """
    if len(sys.argv) < 2:
        raise Exception(
            "No trigger payload provided. Please provide JSON payload as argument."
        )

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    try:
        request = TravelRequest.model_validate(trigger_payload)
    except Exception as e:
        raise Exception(f"Invalid TravelRequest payload: {e}")

    try:
        result = AiTravelAssistant().crew().kickoff(inputs=request.to_crew_inputs())
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
