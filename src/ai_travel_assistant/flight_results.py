"""Parsing of the flight agent's markdown output into tabular data.

The line format parsed here is defined by the prompt in flight_flow.py —
keep the two in sync.
"""

import re

import pandas as pd

FLIGHT_COLUMNS = [
    "Flight No.",
    "Date",
    "Dep. Time",
    "Arr. Time",
    "Journey Time",
    "Stops",
    "Price",
    "Airline",
    "Departure Airport",
    "Arrival Airport",
]


def parse_flight_section(text: str, section: str) -> pd.DataFrame | None:
    """Extract a numbered flight list from one section and return as a DataFrame."""
    pattern = rf"##\s*{re.escape(section)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    rows = []
    for line in match.group(1).strip().splitlines():
        line = line.strip()
        # Match lines starting with a number: "1. ..." or "1) ..."
        if not re.match(r"^\d+[.)]\s", line):
            continue
        # Strip the leading number
        line = re.sub(r"^\d+[.)]\s*", "", line)
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 10:
            rows.append(parts[:10])

    if not rows:
        return None
    return pd.DataFrame(rows, columns=FLIGHT_COLUMNS)
