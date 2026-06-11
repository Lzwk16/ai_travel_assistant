from datetime import date

from crewai import LLM, Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field, model_validator

from ai_travel_assistant.config import GROQ_MODEL, INSIGHTS_FILE, ITINERARY_FILE

RESEARCHER_LLM = LLM(model=GROQ_MODEL, temperature=0.1)  # factual, structured table
WRITER_LLM = LLM(model=GROQ_MODEL, temperature=0.2)  # structured day-by-day
GUIDE_LLM = LLM(model=GROQ_MODEL, temperature=0.4)  # creative recommendations


class TravelRequest(BaseModel):
    origin: str = Field(
        description="The Starting country or city", examples=["Singapore"]
    )
    destinations: list[str] = Field(
        description="List of countries or cities to visit",
        examples=["Tokyo", "Osaka", "Shanghai"],
        min_length=1,
    )
    start_date: date = Field(description="The start date", examples=["2025-06-01"])
    end_date: date = Field(
        description="The end date",
        examples=["2025-06-10"],
    )
    group_size: int = Field(
        description="Number of people travelling",
    )
    budget_type: str = Field(
        description="The type of budget",
        examples=["budget", "mid-range", "luxury"],
        min_length=1,
    )
    interests: list[str] = Field(
        description="List of interests",
        examples=["sightseeing", "food", "local culture"],
        min_length=1,
    )
    travel_style: str = Field(
        description="The travel style",
        examples=["relax", "adventure", "business"],
        min_length=1,
    )
    currency: str = Field(
        default="SGD",
        description="Currency for all cost estimates",
        examples=["SGD", "USD", "JPY"],
    )

    @model_validator(mode="after")
    def check_date_order(self) -> "TravelRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

    @property
    def duration(self) -> int:
        """Automatically calculates trip duration in days."""
        return (self.end_date - self.start_date).days

    def to_crew_inputs(self) -> dict:
        destinations_str = ", ".join(self.destinations)
        return {
            "origin": self.origin,
            "destination": destinations_str,
            "destinations": destinations_str,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "duration": f"{self.duration} days",
            "budget": self.budget_type,
            "group_size": self.group_size,
            "interests": ", ".join(self.interests),
            "travel_style": self.travel_style,
            "currency": self.currency,
        }


@CrewBase
class AiTravelAssistant:
    """AiTravelAssistant crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def travel_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["travel_expert"],  # type: ignore[index]
            llm=RESEARCHER_LLM,
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def local_guide(self) -> Agent:
        return Agent(
            config=self.agents_config["local_expert"],  # type: ignore[index]
            llm=GUIDE_LLM,
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def itinerary_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["travel_consultant"],  # type: ignore[index]
            llm=WRITER_LLM,
            verbose=True,
            tools=[SerperDevTool()],
        )

    @task
    def research_destinations(self) -> Task:
        return Task(
            config=self.tasks_config["destination_analysis"],  # type: ignore[index]
        )

    @task
    def local_insights(self) -> Task:
        return Task(
            config=self.tasks_config["local_expert_insights"],  # type: ignore[index]
            context=[self.research_destinations()],
            output_file=INSIGHTS_FILE,
        )

    @task
    def itinerary_guide(self) -> Task:
        return Task(
            config=self.tasks_config["full_itinerary"],  # type: ignore[index]
            context=[self.research_destinations(), self.local_insights()],
            output_file=ITINERARY_FILE,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AiTravelAssistant crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # ~5 calls/min keeps token usage under Groq's 12K TPM free tier limit
            max_rpm=5,
        )
