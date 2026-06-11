import os
from dataclasses import dataclass

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from serpapi import GoogleSearch

# Cap on options returned to the agent — keeps tool output within the LLM's
# context budget while leaving enough candidates for ranking.
MAX_AGENT_RESULTS = 5


class FlightSearchInput(BaseModel):
    departure_id: str = Field(
        description="IATA airport code for departure (e.g. SIN, NRT, HND, KIX, BKK)"
    )
    arrival_id: str = Field(
        description="IATA airport code for arrival (e.g. SIN, NRT, HND, KIX, BKK)"
    )
    date: str = Field(description="Flight date in YYYY-MM-DD format")
    currency: str = Field(
        default="SGD", description="Currency code (e.g. SGD, USD, JPY)"
    )


def _extract_time(time_str: str) -> str:
    """Return the HH:MM part of a 'YYYY-MM-DD HH:MM' timestamp."""
    parts = time_str.split(" ")
    return parts[-1] if len(parts) == 2 else time_str


@dataclass
class FlightOption:
    """Display-ready fields extracted from one SerpAPI flight option."""

    flight_number: str
    airline: str
    price: str | int
    departure_time: str
    arrival_time: str
    departure_id: str
    arrival_id: str
    departure_name: str
    arrival_name: str
    journey_time: str
    stops_label: str

    @classmethod
    def from_api_option(cls, option: dict) -> "FlightOption | None":
        """Parse a raw SerpAPI option dict; None if it has no flight segments."""
        segments = option.get("flights", [])
        if not segments:
            return None

        first, last = segments[0], segments[-1]
        departure_airport = first.get("departure_airport", {})
        arrival_airport = last.get("arrival_airport", {})
        departure_id = departure_airport.get("id", "?")
        arrival_id = arrival_airport.get("id", "?")

        hours, minutes = divmod(option.get("total_duration", 0), 60)
        num_stops = max(0, len(segments) - 1)
        stops_label = (
            "Nonstop"
            if num_stops == 0
            else f"{num_stops} stop{'s' if num_stops > 1 else ''}"
        )

        return cls(
            flight_number=first.get("flight_number", "?"),
            airline=first.get("airline", "?"),
            price=option.get("price", "?"),
            departure_time=_extract_time(departure_airport.get("time", "")),
            arrival_time=_extract_time(arrival_airport.get("time", "")),
            departure_id=departure_id,
            arrival_id=arrival_id,
            departure_name=departure_airport.get("name", departure_id),
            arrival_name=arrival_airport.get("name", arrival_id),
            journey_time=f"{hours}h {minutes}m",
            stops_label=stops_label,
        )


class GoogleFlightsTool(BaseTool):
    name: str = "Google Flights Search"
    description: str = (
        "Fetches real flight data from Google Flights via SerpAPI. "
        "Returns verified flight numbers, times, airlines, layovers, and prices. "
        "Always supply IATA airport codes — not city names — for departure and "
        "arrival (e.g. SIN=Singapore Changi, NRT=Tokyo Narita, HND=Tokyo Haneda, "
        "KIX=Osaka Kansai). Each call searches one direction only; call twice "
        "for outbound and return legs."
    )
    args_schema: type[BaseModel] = FlightSearchInput

    # ── public entry point (used directly by the flow) ────────────────────────

    def search(
        self,
        departure_id: str,
        arrival_id: str,
        date: str,
        currency: str = "SGD",
    ) -> list[dict]:
        """Return raw option dicts from Google Flights. Empty list on failure."""
        api_key = os.getenv("SERP_API_KEY")
        if not api_key:
            return []
        raw = self._fetch(departure_id, arrival_id, date, currency, api_key)
        if isinstance(raw, str):
            return []
        return raw.get("best_flights") or raw.get("other_flights") or []

    # ── crewai BaseTool entry point (used by agent) ───────────────────────────

    def _run(
        self,
        departure_id: str,
        arrival_id: str,
        date: str,
        currency: str = "SGD",
    ) -> str:
        options = self.search(departure_id, arrival_id, date, currency)
        if not options:
            return (
                f"No flights found for {departure_id.upper()} → "
                f"{arrival_id.upper()} on {date}."
            )
        return self._format_for_agent(
            options[:MAX_AGENT_RESULTS], departure_id, arrival_id, date, currency
        )

    def _format_for_agent(
        self,
        options: list,
        dep: str,
        arr: str,
        date: str,
        currency: str,
    ) -> str:
        """Simple numbered list — easy for the agent to reproduce verbatim."""
        dep, arr = dep.upper(), arr.upper()
        lines = [f"Flights {dep} → {arr} on {date} ({currency}):"]

        for idx, raw_option in enumerate(options, 1):
            option = FlightOption.from_api_option(raw_option)
            if option is None:
                continue
            lines.append(
                f"{idx}. {option.flight_number} | {date} | {option.departure_time} | "
                f"{option.arrival_time} | {option.journey_time} | "
                f"{option.stops_label} | "
                f"{option.price} {currency} | {option.airline} | "
                f"{option.departure_id} – {option.departure_name} | "
                f"{option.arrival_id} – {option.arrival_name}"
            )

        return "\n".join(lines)

    # ── formatting (called by flow after merging multi-airport results) ────────

    @staticmethod
    def format_table(
        options: list[dict],
        dep: str,
        arr: str,
        date: str,
        currency: str,
    ) -> str:
        dep, arr = dep.upper(), arr.upper()
        lines = [
            f"### {dep} → {arr} on {date} ({currency})\n",
            f"| # | Flight No. | Date | Dep. Time | Arr. Time | Journey Time "
            f"| Stops | Price ({currency}) | Airline | Departure Airport "
            f"| Arrival Airport |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]

        for idx, raw_option in enumerate(options, 1):
            option = FlightOption.from_api_option(raw_option)
            if option is None:
                continue
            lines.append(
                f"| {idx} | {option.flight_number} | {date} | {option.departure_time} "
                f"| {option.arrival_time} | {option.journey_time} "
                f"| {option.stops_label} "
                f"| {option.price} | {option.airline} "
                f"| {option.departure_id} – {option.departure_name} "
                f"| {option.arrival_id} – {option.arrival_name} |"
            )

        return "\n".join(lines)

    # ── private helpers ───────────────────────────────────────────────────────

    def _fetch(
        self,
        dep: str,
        arr: str,
        date: str,
        currency: str,
        api_key: str,
    ) -> dict | str:
        try:
            result = GoogleSearch(
                {
                    "engine": "google_flights",
                    "departure_id": dep.upper(),
                    "arrival_id": arr.upper(),
                    "outbound_date": date,
                    "type": "2",
                    "currency": currency,
                    "hl": "en",
                    "adults": 1,
                    "api_key": api_key,
                }
            ).get_dict()

            if "error" in result:
                return f"SerpAPI error: {result['error']}"

            return result

        except Exception as exc:
            return f"Request failed: {exc}"
