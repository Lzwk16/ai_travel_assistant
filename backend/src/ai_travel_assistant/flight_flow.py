"""Flight search flow — deterministic data path, LLM only for airport resolution.


The only genuine reasoning here is resolving city names to IATA airport codes
(incl. multi-airport cities). That stays with the LLM — a short, validated,
low-risk output. Everything that touches real numbers (search, the 1.5×
journey-time filter, ranking, formatting) is now deterministic code working from
the tool's real ``FlightOption`` data.
"""

import re
from datetime import date

from crewai import LLM
from crewai.flow.flow import Flow, start
from pydantic import BaseModel, Field, model_validator

from ai_travel_assistant.config import (
    FLIGHT_OPTIONS_FILE,
    GROQ_MODEL,
    ensure_outputs_dir,
)
from ai_travel_assistant.tools.google_flights import FlightOption, GoogleFlightsTool

# Temperature 0: airport-code resolution should be as deterministic as possible.
AIRPORT_LLM = LLM(model=GROQ_MODEL, temperature=0)

# Flights presented per direction.
TOP_N = 5

# Discard any option whose journey time exceeds this multiple of the shortest
# found in that direction (no absurd long-haul connections).
_MAX_JOURNEY_FACTOR = 1.5

# Ranking weights: price, total journey time, number of stops.
_W_PRICE, _W_TIME, _W_STOPS = 0.4, 0.4, 0.2


class FlightRequest(BaseModel):
    origin: str = Field(description="Departure city", examples=["Singapore"])
    destinations: list[str] = Field(
        description="List of destination cities",
        examples=["Tokyo", "Osaka"],
        min_length=1,
    )
    start_date: date = Field(
        description="Outbound departure date", examples=["2025-06-01"]
    )
    end_date: date = Field(
        description="Return date",
        examples=["2025-06-10"],
    )
    currency: str = Field(
        default="SGD",
        description="Currency for price display",
        examples=["SGD", "USD", "JPY"],
    )
    adults: int = Field(
        default=1,
        ge=1,
        description="Number of adult passengers",
        examples=[1, 2],
    )

    @model_validator(mode="after")
    def check_date_order(self) -> "FlightRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

    def to_flow_inputs(self) -> dict:
        return {
            "origin": self.origin,
            "destination": ", ".join(self.destinations),
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "currency": self.currency,
            "adults": self.adults,
        }


def _resolve_airports(city_str: str) -> list[str]:
    """Resolve a city (or comma-joined cities) to major international airport IATA
    codes via the LLM. Codes are extracted by regex, so prose around them is
    tolerated; bogus codes simply yield empty searches and drop out."""
    prompt = (
        "List the IATA codes of the major international airports serving: "
        f"{city_str}. Include all major airports for multi-airport cities "
        "(e.g. Tokyo -> NRT, HND; London -> LHR, LGW; Paris -> CDG, ORY). "
        "Respond with only the 3-letter codes separated by commas."
    )
    response = AIRPORT_LLM.call(prompt)
    codes: list[str] = []
    for code in re.findall(r"\b[A-Z]{3}\b", str(response).upper()):
        if code not in codes:
            codes.append(code)
    return codes


def _stops(option: dict) -> int:
    return max(0, len(option.get("flights", [])) - 1)


def _rank_flights(options: list[dict], top_n: int) -> list[dict]:
    """Filter by the journey-time cap, then rank by best balance of price,
    journey time, and stops (each min-max normalised within the set)."""
    usable = [
        r
        for r in options
        if isinstance(r.get("price"), (int, float))
        and isinstance(r.get("total_duration"), (int, float))
    ]
    if not usable:
        return []

    shortest = min(r["total_duration"] for r in usable)
    usable = [
        r for r in usable if r["total_duration"] <= _MAX_JOURNEY_FACTOR * shortest
    ]

    prices = [r["price"] for r in usable]
    durations = [r["total_duration"] for r in usable]
    stops = [_stops(r) for r in usable]
    pmin, pmax = min(prices), max(prices)
    tmin, tmax = min(durations), max(durations)
    smin, smax = min(stops), max(stops)

    def score(r: dict) -> float:
        price_s = 1 - (r["price"] - pmin) / (pmax - pmin) if pmax > pmin else 1.0
        time_s = (
            1 - (r["total_duration"] - tmin) / (tmax - tmin) if tmax > tmin else 1.0
        )
        stop_s = 1 - (_stops(r) - smin) / (smax - smin) if smax > smin else 1.0
        return _W_PRICE * price_s + _W_TIME * time_s + _W_STOPS * stop_s

    return sorted(usable, key=score, reverse=True)[:top_n]


def _format_section(
    title: str, ranked: list[dict], date_str: str, currency: str
) -> str:
    lines = [f"## {title}"]
    rank = 0
    for raw in ranked:
        option = FlightOption.from_api_option(raw)
        if option is None:
            continue
        rank += 1
        lines.append(
            f"{rank}. {option.flight_number} | {date_str} | {option.departure_time} "
            f"| {option.arrival_time} | {option.journey_time} | {option.stops_label} "
            f"| {option.price} {currency} | {option.airline} "
            f"| {option.departure_id} – {option.departure_name} "
            f"| {option.arrival_id} – {option.arrival_name}"
        )
    if rank == 0:
        lines.append("No flights found.")
    return "\n".join(lines)


class FlightSearchFlow(Flow):
    @start()
    def search_flights(self) -> str:
        origin = self.state["origin"]
        destination = self.state["destination"]
        start_date = self.state["start_date"]
        end_date = self.state["end_date"]
        currency = self.state["currency"]
        adults = self.state["adults"]

        origin_codes = _resolve_airports(origin)
        dest_codes = _resolve_airports(destination)
        tool = GoogleFlightsTool(adults=adults)

        outbound: list[dict] = []
        returning: list[dict] = []
        for o in origin_codes:
            for d in dest_codes:
                outbound += tool.search(o, d, start_date, currency)
                returning += tool.search(d, o, end_date, currency)

        markdown = "{}\n\n{}".format(
            _format_section(
                "Outbound Flights", _rank_flights(outbound, TOP_N), start_date, currency
            ),
            _format_section(
                "Return Flights", _rank_flights(returning, TOP_N), end_date, currency
            ),
        )
        ensure_outputs_dir()
        with open(FLIGHT_OPTIONS_FILE, "w", encoding="utf-8") as f:
            f.write(markdown)
        return markdown
