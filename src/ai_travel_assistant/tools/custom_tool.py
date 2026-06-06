import os
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


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


class GoogleFlightsTool(BaseTool):
    name: str = "Google Flights Search"
    description: str = (
        "Fetches real flight data from Google Flights via SerpAPI. "
        "Returns verified flight numbers, times, airlines, layovers, and prices. "
        "Always supply IATA airport codes — not city names — for departure and arrival "
        "(e.g. SIN=Singapore Changi, NRT=Tokyo Narita, HND=Tokyo Haneda, KIX=Osaka Kansai). "
        "Each call searches one direction only; call twice for outbound and return legs."
    )
    args_schema: Type[BaseModel] = FlightSearchInput

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
        return self._format_for_agent(options[:5], departure_id, arrival_id, date, currency)

    def _format_for_agent(
        self,
        options: list,
        dep: str,
        arr: str,
        date: str,
        currency: str,
    ) -> str:
        """Simple numbered list — easy for the agent to reproduce in its final answer."""
        dep, arr = dep.upper(), arr.upper()
        lines = [f"Flights {dep} → {arr} on {date} ({currency}):"]

        for idx, option in enumerate(options, 1):
            segments = option.get("flights", [])
            if not segments:
                continue

            first, last = segments[0], segments[-1]
            flight_num = first.get("flight_number", "?")
            airline = first.get("airline", "?")
            price = option.get("price", "?")

            dep_airport = first.get("departure_airport", {})
            arr_airport = last.get("arrival_airport", {})

            dep_time = self._extract_time(dep_airport.get("time", ""))
            arr_time = self._extract_time(arr_airport.get("time", ""))
            dep_id = dep_airport.get("id", "?")
            arr_id = arr_airport.get("id", "?")
            dep_name = dep_airport.get("name", dep_id)
            arr_name = arr_airport.get("name", arr_id)

            total_min = option.get("total_duration", 0)
            h, m = divmod(total_min, 60)
            journey = f"{h}h {m}m"

            num_stops = max(0, len(segments) - 1)
            stops_label = "Nonstop" if num_stops == 0 else f"{num_stops} stop{'s' if num_stops > 1 else ''}"

            lines.append(
                f"{idx}. {flight_num} | {date} | {dep_time} | {arr_time} | "
                f"{journey} | {stops_label} | {price} {currency} | {airline} | "
                f"{dep_id} – {dep_name} | {arr_id} – {arr_name}"
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
            f"| # | Flight No. | Date | Dep. Time | Arr. Time | Journey Time | Stops | Price ({currency}) | Airline | Departure Airport | Arrival Airport |",
            f"|---|---|---|---|---|---|---|---|---|---|---|",
        ]

        for idx, option in enumerate(options, 1):
            segments = option.get("flights", [])
            if not segments:
                continue

            first, last = segments[0], segments[-1]
            flight_num = first.get("flight_number", "?")
            airline = first.get("airline", "?")
            price = option.get("price", "?")

            dep_airport = first.get("departure_airport", {})
            arr_airport = last.get("arrival_airport", {})

            dep_time = GoogleFlightsTool._extract_time(dep_airport.get("time", ""))
            arr_time = GoogleFlightsTool._extract_time(arr_airport.get("time", ""))
            dep_id = dep_airport.get("id", "?")
            arr_id = arr_airport.get("id", "?")
            dep_name = dep_airport.get("name", dep_id)
            arr_name = arr_airport.get("name", arr_id)

            total_min = option.get("total_duration", 0)
            h, m = divmod(total_min, 60)
            journey = f"{h}h {m}m"

            num_stops = max(0, len(segments) - 1)
            stops_label = "Nonstop" if num_stops == 0 else f"{num_stops} stop{'s' if num_stops > 1 else ''}"

            lines.append(
                f"| {idx} | {flight_num} | {date} | {dep_time} | {arr_time} "
                f"| {journey} | {stops_label} | {price} | {airline} "
                f"| {dep_id} – {dep_name} | {arr_id} – {arr_name} |"
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
            from serpapi import GoogleSearch
            result = GoogleSearch({
                "engine": "google_flights",
                "departure_id": dep.upper(),
                "arrival_id": arr.upper(),
                "outbound_date": date,
                "type": "2",
                "currency": currency,
                "hl": "en",
                "adults": 1,
                "api_key": api_key,
            }).get_dict()

            if "error" in result:
                return f"SerpAPI error: {result['error']}"

            return result

        except Exception as exc:
            return f"Request failed: {exc}"

    @staticmethod
    def _extract_time(time_str: str) -> str:
        parts = time_str.split(" ")
        return parts[-1] if len(parts) == 2 else time_str
