import os

from crewai import Agent, LLM
from crewai.flow.flow import Flow, start
from crewai_tools import SerperDevTool
from datetime import date
from pydantic import BaseModel, Field

flight_settings = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.1)


class FlightRequest(BaseModel):
    origin: str = Field(description="Departure city or country", examples=["Singapore"])
    destinations: list[str] = Field(
        description="List of destination cities or countries",
        examples=["Tokyo", "Osaka"],
        min_length=1,
    )
    start_date: date = Field(description="Outbound departure date", examples=["2025-06-01"])
    end_date: date = Field(
        description="Return date (include for round-trip search)", examples=["2025-06-10"]
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
        agent = Agent(
            role=f"Flight Deals Expert for {self.state['destination']}",
            goal=(
                f"Find the best flight deals from {self.state['origin']} to "
                f"{self.state['destination']} departing {self.state['start_date']}, "
                f"returning {self.state['end_date']}. "
                f"Provide all prices in {self.state['currency']}."
            ),
            backstory=(
                "You are an expert flight deals agent with a knack for finding the best deals "
                "across destinations globally. You excel at comparing flights based on ticket prices, "
                "flight times, availability, and connecting airports. You provide data-driven "
                "recommendations with clear reasoning."
            ),
            llm=flight_settings,
            tools=[SerperDevTool()],
            verbose=True,
        )

        prompt = (
            f"Find the best flights from {self.state['origin']} to {self.state['destination']}.\n"
            f"Departure date: {self.state['start_date']}\n"
            f"Return date: {self.state['end_date']}\n\n"
            f"List 5 flight options. For each include:\n"
            f"- Flight Number\n"
            f"- Flight Date\n"
            f"- Departure Time\n"
            f"- Arrival Time\n"
            f"- Price/Fare (in {self.state['currency']})\n"
            f"- Airline Name\n"
            f"- Departure Airport\n"
            f"- Arrival Airport\n"
        )

        result = agent.kickoff(messages=prompt)

        os.makedirs("outputs", exist_ok=True)
        with open("outputs/flight_options.md", "w") as f:
            f.write(result.raw)

        return result.raw
