from datetime import date

from crewai import LLM, Agent
from crewai.flow.flow import Flow, start
from pydantic import BaseModel, Field, model_validator

from ai_travel_assistant.config import (
    FLIGHT_OPTIONS_FILE,
    GROQ_MODEL,
    ensure_outputs_dir,
)
from ai_travel_assistant.tools.google_flights import GoogleFlightsTool

FLIGHT_LLM = LLM(model=GROQ_MODEL, temperature=0.1)

FLIGHT_AGENT_BACKSTORY = (
    "You are a seasoned flight research specialist who has booked thousands of "
    "trips across Asia and beyond. You know that major cities often have multiple "
    "airports — Tokyo has Narita (NRT) and Haneda (HND), London has Heathrow (LHR) "
    "and Gatwick (LGW), Paris has Charles de Gaulle (CDG) and Orly (ORY) — and you "
    "always search all relevant airports to give travellers the full picture. "
    "When evaluating options, you weigh price (40%), total journey time (40%), "
    "and number of stops (20%). You never recommend an option whose total journey "
    "time exceeds 1.5 times the shortest available option, no matter how cheap it is. "
    "You only present flight data retrieved directly from your search tool — "
    "you never fabricate flight numbers, times, or fares."
)


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
        }


def _build_flight_agent(
    origin: str, destination: str, start_date: str, end_date: str, currency: str
) -> Agent:
    return Agent(
        role=f"Senior Flight Research Specialist for {origin} to {destination} routes",
        goal=(
            f"Find the 5 best-value outbound flights from {origin} to {destination} "
            f"departing on {start_date}, and the 5 best return flights from "
            f"{destination} to {origin} on {end_date}. All prices in {currency}. "
            f"Some cities are served by multiple major airports — search all of them "
            f"and compare across airports to surface the best options overall. "
            f"Balance price, total journey time, and number of stops: do not recommend "
            f"a long connecting flight when a reasonably priced nonstop or "
            f"short-connection option exists."
        ),
        backstory=FLIGHT_AGENT_BACKSTORY,
        llm=FLIGHT_LLM,
        tools=[GoogleFlightsTool()],
        verbose=True,
    )


def _build_search_prompt(
    origin: str, destination: str, start_date: str, end_date: str, currency: str
) -> str:
    return (
        f"Find the best flights for this round trip:\n"
        f"  Origin: {origin}\n"
        f"  Destination: {destination}\n"
        f"  Outbound date: {start_date}\n"
        f"  Return date: {end_date}\n"
        f"  Currency: {currency}\n\n"
        f"Steps:\n"
        f"1. Identify all major international airports serving {origin} "
        f"and {destination}. "
        f"Convert each city to its IATA airport codes "
        f"(e.g. Tokyo → NRT and HND, Singapore → SIN).\n"
        f"2. Call the Google Flights Search tool for each outbound airport pair "
        f"({origin} airports → {destination} airports) on {start_date}.\n"
        f"3. Call the Google Flights Search tool for each return airport pair "
        f"({destination} airports → {origin} airports) on {end_date}.\n"
        f"4. Compare all results. Discard any option whose total journey time "
        f"is more than 1.5× the shortest journey time found. From the remaining "
        f"options, select the top 5 for outbound and top 5 for return, ranked by "
        f"best balance of price, journey time, and stops.\n"
        f"5. Present results under two sections: '## Outbound Flights' and "
        f"'## Return Flights'.\n"
        f"6. Under each section, list each selected flight on one line in exactly "
        f"this format:\n"
        f"   N. FlightNo | Date | DepTime | ArrTime | JourneyTime | Stops "
        f"| Price {currency} | Airline | DepCode – DepAirportName "
        f"| ArrCode – ArrAirportName\n"
        f"   Example: 1. SQ 12 | {start_date} | 09:25 | 17:30 | 7h 5m | Nonstop "
        f"| 816 {currency} | Singapore Airlines | SIN – Singapore Changi Airport "
        f"| NRT – Narita International Airport\n"
        f"7. Do not add commentary, explanations, or any text outside these "
        f"two sections."
    )


class FlightSearchFlow(Flow):
    @start()
    def search_flights(self) -> str:
        origin = self.state["origin"]
        destination = self.state["destination"]
        start_date = self.state["start_date"]
        end_date = self.state["end_date"]
        currency = self.state["currency"]

        agent = _build_flight_agent(origin, destination, start_date, end_date, currency)
        prompt = _build_search_prompt(
            origin, destination, start_date, end_date, currency
        )
        result = agent.kickoff(messages=prompt)

        ensure_outputs_dir()
        with open(FLIGHT_OPTIONS_FILE, "w") as f:
            f.write(result.raw)

        return result.raw
