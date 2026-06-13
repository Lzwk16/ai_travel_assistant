# AI Travel Assistant

A multi-agent AI travel planning system that researches destinations, gathers local insights, and finds real flights, all from a simple Streamlit interface.

## Overview

AI Travel Assistant automates travel research and planning through two
independent modes. **Plan itinerary** runs three specialised AI agents in
sequence to analyse destinations, surface local insights, and produce a detailed
day-by-day schedule. **Find flights** uses a dedicated agent backed by real
Google Flights data to search multiple airports per city, filter poor timing connections, and rank options by a balanced score of price, journey time, and
stops.

## Architecture

```
ai_travel_assistant/
├── app.py                           # Streamlit UI with mode selector, forms, result display
├── src/ai_travel_assistant/
│   ├── config.py                    # Shared constants: Groq model id, output file paths
│   ├── crew.py                      # TravelRequest model + AiTravelAssistant crew (3 agents)
│   ├── flight_flow.py               # FlightRequest model + FlightSearchFlow + inline flight agent
│   ├── flight_results.py            # Parses flight agent markdown output into DataFrames
│   ├── main.py                      # CLI entry points (run, train, test, replay)
│   ├── tools/
│   │   └── google_flights.py        # GoogleFlightsTool for SerpAPI Google Flights integration
│   └── config/
│       ├── agents.yaml              # Role, goal, backstory for the 3 itinerary crew agents
│       └── tasks.yaml               # Task descriptions and expected outputs
└── outputs/
    ├── recommended_insights.md      # Local Guide output
    ├── suggested_itinerary.md       # Itinerary Writer output
    └── flight_options.md            # FlightSearchFlow output
```

### Mode 1 — Plan itinerary (`AiTravelAssistant` crew)

Three agents run sequentially; each agent's output is passed as context to the next.

```
TravelRequest
      │
      ▼
┌─────────────────────┐
│  Travel Researcher  │  Web search via SerperDevTool
│                     │
│                     │  • Analyses every destination (weather, cost, activities)
│                     │  • Decides how to split days across destinations
│                     │    based on travel style and interests
│                     │  → Day-distribution table: Destination | Days | Reasoning
└────────┬────────────┘
         │ context
         ▼
┌─────────────────────┐
│    Local Guide      │  Web search via SerperDevTool
│                     │
│                     │  • Provides insider knowledge for every destination
│                     │  • Scales depth of recommendations to days allocated
│                     │  → outputs/recommended_insights.md
└────────┬────────────┘
         │ context (both agents above)
         ▼
┌─────────────────────┐
│  Itinerary Writer   │  Web search via SerperDevTool
│                     │
│                     │  • Builds day-by-day schedule in destination blocks
│                     │  • Honours the day-distribution table from Travel Researcher
│                     │  • Labels transit days between destinations explicitly
│                     │  → outputs/suggested_itinerary.md
└─────────────────────┘
```

**Day distribution logic**

The Travel Researcher decides how to split the trip duration across destinations:

| Travel style | Behaviour |
|---|---|
| `relax` | Depth over breadth: more days per destination, fewer moves |
| `adventure` | More stops, shorter stays, optimised for variety |
| `business` | Anchors around business commitments first, fills gaps with sightseeing |

Transit time between destinations is always accounted for (minimum half a day).

### Mode 2 — Find flights (`FlightSearchFlow` flow)

A single-step crewAI Flow that runs a dedicated flight research agent backed by real Google Flights data via SerpAPI. Returns verified, structured results with no hallucinated flight numbers or times.

```
FlightRequest
      │
      ▼
┌───────────────────────────────────────────────────────────────────┐
│  FlightSearchFlow  →  Flight Research Agent                       │
│                                                                   │
│  • Resolves city names to IATA codes (e.g. Tokyo → NRT + HND)     │
│  • Calls GoogleFlightsTool (SerpAPI) for each airport pair        │
│  • Searches all major airports per city (multi-airport cities)    │
│  • Filters options whose journey time > 1.5× the shortest found   │
│  • Ranks remaining options: price 40% / journey time 40% /        │
│    stops 20% — selects top 5 outbound + top 5 return              │
│  → outputs/flight_options.md                                      │
└───────────────────────────────────────────────────────────────────┘
```

**Multi-airport city support**

The agent knows that several cities have more than one major international airport and always searches all of them:

| City | Airports searched |
|---|---|
| Tokyo | NRT (Narita) + HND (Haneda) |
| London | LHR (Heathrow) + LGW (Gatwick) |
| Paris | CDG (Charles de Gaulle) + ORY (Orly) |

End users type city names in the Streamlit form as the agent resolves IATA codes automatically.

**Output columns**

Results render as two labelled DataFrames in Streamlit (`Outbound Flights` / `Return Flights`):

| Column | Description |
|---|---|
| Flight No. | Airline + flight number |
| Date | Departure date |
| Dep. Time | Departure time (local) |
| Arr. Time | Arrival time (local) |
| Journey Time | Total elapsed time including connections |
| Stops | Nonstop / 1 stop / 2 stops |
| Price | Fare in the selected currency |
| Airline | Operating carrier |
| Departure Airport | IATA code + full airport name |
| Arrival Airport | IATA code + full airport name |

## Installation & Setup

**Prerequisites**

- Python `>=3.10, <3.14`
- [uv](https://docs.astral.sh/uv/) — `pip install uv`

**Install dependencies**

```bash
git clone <repo-url>
cd ai_travel_assistant
crewai install
```

**Environment variables**

Create a `.env` file in the project root:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | LLM provider — [console.groq.com](https://console.groq.com) (free tier available) |
| `SERPER_API_KEY` | Yes | Web search for itinerary crew agents — [serper.dev](https://serper.dev) (free: 2,500 searches) |
| `SERP_API_KEY` | Yes | Google Flights data for flight search agent — [serpapi.com](https://serpapi.com) (free: 250 searches/month) |

## Usage

**Streamlit UI (recommended)**

```bash
uv run streamlit run app.py
```

Opens at `http://localhost:8501`. Select a mode at the top:

- **Plan itinerary** — fill in origin, destinations, dates, group size, budget, travel style, and interests, then click **Plan My Trip**. Results appear in two tabs: full itinerary and local insights, each downloadable as Markdown.
- **Find flights** — fill in origin, destination, departure date, return date, and currency, then click **Find Flights**. Results render as two DataFrames (outbound and return), downloadable as Markdown.

**CLI (itinerary crew only)**

```bash
crewai run
```

Edit `SAMPLE_REQUEST` in `src/ai_travel_assistant/main.py` to change trip inputs:

```python
SAMPLE_REQUEST = TravelRequest(
    origin="Singapore",
    destinations=["Tokyo", "Osaka"],
    start_date=date(2025, 9, 1),
    end_date=date(2025, 9, 10),
    group_size=2,
    budget_type="mid-range",    # "budget" | "mid-range" | "luxury"
    interests=["food", "local culture", "sightseeing"],
    travel_style="relax",       # "relax" | "adventure" | "business"
    currency="SGD",
)
```

Outputs are written to `outputs/recommended_insights.md` and `outputs/suggested_itinerary.md`.

**Changing the LLM**

Both `crew.py` and `flight_flow.py` use [LiteLLM](https://docs.litellm.ai/docs/providers) provider/model format:

```python
llm = "groq/llama-3.3-70b-versatile"

# Other examples:
# llm = "anthropic/claude-sonnet-4-20250514"
# llm = "openai/gpt-4o"
```

Add the corresponding API key to `.env`.

**Modifying agent behaviour**

| File | What to change |
|---|---|
| `config/agents.yaml` | Role, goal, and backstory for the 3 itinerary crew agents |
| `config/tasks.yaml` | Task instructions and expected outputs for the itinerary crew |
| `crew.py` | Tools, LLM settings, and task context wiring for the itinerary crew |
| `flight_flow.py` | Flight agent role/goal/backstory, prompt, and LLM settings |
| `tools/google_flights.py` | SerpAPI parameters, response parsing, and output formatting |

## Future work

1. API & Front-end development for more user friendly interface
2. Include advanced reasoning, planning, collaboration, and state memory into
   agents for more complex and detailed itinerary planning
3. Infrastructure & deployment: Docker containerisation, observability, and evaluation
