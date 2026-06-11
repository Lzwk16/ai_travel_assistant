"""Shared configuration: model identifiers and output file locations.

Both the producers (crew tasks, flight flow) and the consumer (Streamlit app)
reference these paths, so they must stay defined in exactly one place.
"""

import os

GROQ_MODEL = "groq/llama-3.3-70b-versatile"

OUTPUTS_DIR = "outputs"
FLIGHT_OPTIONS_FILE = f"{OUTPUTS_DIR}/flight_options.md"
INSIGHTS_FILE = f"{OUTPUTS_DIR}/recommended_insights.md"
ITINERARY_FILE = f"{OUTPUTS_DIR}/suggested_itinerary.md"


def ensure_outputs_dir() -> None:
    """Create the outputs directory if it does not already exist."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
