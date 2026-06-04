import os

from crewai import Agent, LLM
from crewai.flow.flow import Flow, start
from datetime import date
from pydantic import BaseModel, Field

from ai_travel_assistant.tools.custom_tool import GoogleFlightsTool

flight_settings = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.1)


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

    def to_flow_inputs(self) -> dict:
        return {
            "origin": self.origin,
            "destination": ", ".join(self.destinations),
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "currency": self.currency,
        }


class FlightSearchFlow(Flow):
    @start()
    def search_flights(self) -> str:
        origin = self.state["origin"]
        destination = self.state["destination"]
        start_date = self.state["start_date"]
        end_date = self.state["end_date"]
        currency = self.state["currency"]

        agent = Agent(
            role=f"Senior Flight Research Specialist for {origin} to {destination} routes",
            goal=(
                f"Find the 5 best-value outbound flights from {origin} to {destination} "
                f"departing on {start_date}, and the 5 best return flights from {destination} "
                f"to {origin} on {end_date}. All prices in {currency}. "
                f"Some cities are served by multiple major airports — search all of them "
                f"and compare across airports to surface the best options overall. "
                f"Balance price, total journey time, and number of stops: do not recommend "
                f"a long connecting flight when a reasonably priced nonstop or short-connection "
                f"option exists."
            ),
            backstory=(
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
            ),
            llm=flight_settings,
            tools=[GoogleFlightsTool()],
            verbose=True,
        )

        prompt = (
            f"Find the best flights for this round trip:\n"
            f"  Origin: {origin}\n"
            f"  Destination: {destination}\n"
            f"  Outbound date: {start_date}\n"
            f"  Return date: {end_date}\n"
            f"  Currency: {currency}\n\n"
            f"Steps:\n"
            f"1. Identify all major international airports serving {origin} and {destination}. "
            f"Convert each city to its IATA airport codes "
            f"(e.g. Tokyo → NRT and HND, Singapore → SIN).\n"
            f"2. Call the Google Flights Search tool for each outbound airport pair "
            f"({origin} airports → {destination} airports) on {start_date}.\n"
            f"3. Call the Google Flights Search tool for each return airport pair "
            f"({destination} airports → {origin} airports) on {end_date}.\n"
            f"4. Compare all results. Discard any option whose total journey time is more than "
            f"1.5× the shortest journey time found. From the remaining options, select the top 5 "
            f"for outbound and top 5 for return, ranked by best balance of price, journey time, "
            f"and stops.\n"
            f"5. Present results under two sections: '## Outbound Flights' and '## Return Flights'.\n"
            f"6. Under each section, list each selected flight on one line in exactly this format:\n"
            f"   N. FlightNo | Date | DepTime | ArrTime | JourneyTime | Stops | Price {currency} | Airline | DepCode – DepAirportName | ArrCode – ArrAirportName\n"
            f"   Example: 1. SQ 12 | {start_date} | 09:25 | 17:30 | 7h 5m | Nonstop | 816 {currency} | Singapore Airlines | SIN – Singapore Changi Airport | NRT – Narita International Airport\n"
            f"7. Do not add commentary, explanations, or any text outside these two sections."
        )

        result = agent.kickoff(messages=prompt)

        os.makedirs("outputs", exist_ok=True)
        with open("outputs/flight_options.md", "w") as f:
            f.write(result.raw)

        return result.raw
