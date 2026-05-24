import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import SerperDevTool

from datetime import date
from pydantic import BaseModel, Field

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

_MODEL = "groq/llama-3.3-70b-versatile"
_LLM_RESEARCHER = LLM(model=_MODEL, temperature=0.1)   # factual, structured table
_LLM_WRITER = LLM(model=_MODEL, temperature=0.2)       # structured day-by-day
_LLM_GUIDE = LLM(model=_MODEL, temperature=0.4)        # creative recommendations
_LLM_FLIGHTS = LLM(model=_MODEL, temperature=0.1)      # factual flight data


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

    @property
    def duration(self) -> int:
        """Automatically calculates trip duration in days."""
        return (self.end_date - self.start_date).days

    def to_crew_inputs(self) -> dict:
        """
        Converts the model into the exact dictionary format
        and string-joined values required by your tasks.yaml.
        """
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

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def flight_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["flight_expert"],  # type: ignore[index]
            llm=_LLM_FLIGHTS,
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def travel_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["travel_expert"],  # type: ignore[index]
            llm=_LLM_RESEARCHER,
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def local_guide(self) -> Agent:
        return Agent(
            config=self.agents_config["local_expert"],  # type: ignore[index]
            llm=_LLM_GUIDE,
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def itinerary_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["travel_consultant"],  # type: ignore[index]
            llm=_LLM_WRITER,
            verbose=True,
            tools=[SerperDevTool()],
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def find_flights(self) -> Task:
        return Task(
            config=self.tasks_config["flight_research"],  # type: ignore[index]
            output_file="outputs/flight_options.md",
        )

    @task
    def research_destinations(self) -> Task:
        return Task(
            config=self.tasks_config["destination_analysis"],  # type: ignore[index]
            context=[self.find_flights()],
        )

    @task
    def local_insights(self) -> Task:
        return Task(
            config=self.tasks_config["local_expert_insights"],  # type: ignore[index]
            context=[self.research_destinations()],
            output_file="outputs/recommended_insights.md",
        )

    @task
    def itinerary_guide(self) -> Task:
        return Task(
            config=self.tasks_config["full_itinerary"],  # type: ignore[index]
            context=[self.find_flights(), self.research_destinations(), self.local_insights()],
            output_file="outputs/suggested_itinerary.md",
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AiTravelAssistant crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
