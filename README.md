# AI Travel Assistant

A multi-agent AI travel planning system built with [crewAI](https://crewai.com). The app offers two independent modes — **Plan Itinerary** and **Find Flights** — each backed by a different crewAI architectural pattern chosen to match the complexity and precision requirements of that task.

## Architecture

### Mode 1 — Plan Itinerary (`AiTravelAssistant` Crew)

Three agents run sequentially. Each agent's output is passed as context to the next.

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

**Day Distribution Logic**

The Travel Researcher decides how to split the trip duration across multiple destinations:

| Travel Style | Behaviour |
|---|---|
| `relax` | Depth over breadth: more days per destination, fewer moves |
| `adventure` | More stops, shorter stays, optimised for variety |
| `business` | Anchors around business commitments first, fills gaps with sightseeing |

Transit time between destinations is always accounted for (minimum half a day).

---

### Mode 2 — Find Flights (`FlightSearchFlow` Flow)

A single-step crewAI Flow via LLM API call with structured output. Skips the task-planning overhead of a full Crew and reduces token consumption.

```
FlightRequest
      │
      ▼
┌───────────────────────────────────────────────────┐
│  FlightSearchFlow                                 │
│                                                   │
│  • Web search via SerperDevTool                   │
│  • Searches for 5 flight options (outbound+return)│
│  • Compares price, times, airlines, airports      │
│  → outputs/flight_options.md                      │
└───────────────────────────────────────────────────┘
```

---

### Source Files

| File | Purpose |
|---|---|
| `src/ai_travel_assistant/crew.py` | `TravelRequest` model + `AiTravelAssistant` crew (3 agents) |
| `src/ai_travel_assistant/flight_flow.py` | `FlightRequest` model + `FlightSearchFlow` |
| `src/ai_travel_assistant/config/agents.yaml` | Agent role, goal, backstory for the itinerary crew |
| `src/ai_travel_assistant/config/tasks.yaml` | Task descriptions and expected outputs for the itinerary crew |
| `app.py` | Streamlit UI — mode selector, forms, result display |
| `main.py` | CLI entry points (`run`, `train`, `test`, `replay`) for the itinerary crew |

---

### Input Models

**`TravelRequest`** — used by Plan Itinerary mode (`crew.py`)

| Field | Type | Description | Example |
|---|---|---|---|
| `origin` | `str` | Departure city/country | `"Singapore"` |
| `destinations` | `list[str]` | All cities/countries to visit | `["Tokyo", "Osaka"]` |
| `start_date` | `date` | Trip start date | `date(2025, 9, 1)` |
| `end_date` | `date` | Trip end date | `date(2025, 9, 10)` |
| `group_size` | `int` | Number of travellers | `2` |
| `budget_type` | `str` | `"budget"`, `"mid-range"`, or `"luxury"` | `"mid-range"` |
| `interests` | `list[str]` | Activities of interest | `["food", "local culture"]` |
| `travel_style` | `str` | `"relax"`, `"adventure"`, or `"business"` | `"relax"` |
| `currency` | `str` | Currency for all cost estimates (default: `"SGD"`) | `"SGD"` |

**`FlightRequest`** — used by Find Flights mode (`flight_flow.py`)

| Field | Type | Description | Example |
|---|---|---|---|
| `origin` | `str` | Departure city/country | `"Singapore"` |
| `destinations` | `list[str]` | Destination cities/countries | `["Tokyo"]` |
| `start_date` | `date` | Outbound departure date | `date(2025, 9, 1)` |
| `end_date` | `date` | Return date | `date(2025, 9, 10)` |
| `currency` | `str` | Currency for price display (default: `"SGD"`) | `"SGD"` |

---

### Output Files

| File | Produced by | Contents |
|---|---|---|
| `outputs/recommended_insights.md` | Local Guide (itinerary crew) | Per-destination insider guide scaled to days allocated |
| `outputs/suggested_itinerary.md` | Itinerary Writer (itinerary crew) | Full day-by-day schedule with accommodation, dining, transport, and budget breakdown |
| `outputs/flight_options.md` | FlightSearchFlow | 5 flight options with number, times, price, airline, and airports |

---

## Environment Setup

### Prerequisites

- Python `>=3.10, <3.14`
- [uv](https://docs.astral.sh/uv/) — install with `pip install uv`

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd ai_travel_assistant
crewai install        # installs all dependencies via uv
```

### 2. Configure environment variables

Create a `.env` and fill in the required keys:

```bash
# LLM provider — project uses Groq by default
# You may use other proprietary model providers as needed
GROQ_API_KEY=your_groq_api_key

# Web search tool used by agents
SERPER_API_KEY=your_serper_api_key
```

Get your API keys here:
- **Groq**: [console.groq.com](https://console.groq.com) (free tier available)
- **Serper**: [serper.dev](https://serper.dev) (free tier: 2,500 searches)

### 3. Run

**Streamlit UI (recommended)**

```bash
uv run streamlit run app.py
```

Opens at `http://localhost:8501`. Use the mode selector at the top:
- **Plan Itinerary** — fill in the full trip form and click **Plan My Trip** to run the 3-agent crew
- **Find Flights** — fill in the flight form and click **Find Flights** to run the flow

**CLI (itinerary crew only)**

```bash
crewai run
```

Edit `_SAMPLE_REQUEST` in `main.py` to change the trip inputs. Outputs are written to `outputs/recommended_insights.md` and `outputs/suggested_itinerary.md`.

---

## Configuration

### Changing the travel request (CLI)

Edit `_SAMPLE_REQUEST` in `src/ai_travel_assistant/main.py`:

```python
_SAMPLE_REQUEST = TravelRequest(
    origin="Singapore",
    destinations=["Tokyo", "Osaka"],   # all destinations will be visited
    start_date=date(2025, 9, 1),
    end_date=date(2025, 9, 10),
    group_size=2,
    budget_type="mid-range",           # "budget" | "mid-range" | "luxury"
    interests=["food", "local culture", "sightseeing"],
    travel_style="relax",              # "relax" | "adventure" | "business"
    currency="SGD",
)
```

### Changing the LLM model

The itinerary crew agents are configured via LLM settings at the top of `crew.py`. The flight flow agent is configured at the top of `flight_flow.py`. Both use [LiteLLM](https://docs.litellm.ai/docs/providers) provider/model format:

```python
# crew.py / flight_flow.py
llm = "groq/llama-3.3-70b-versatile"   # change this line

# Other examples:
# llm = "anthropic/claude-sonnet-4-20250514"
# llm = "openai/gpt-4o"
```

Add the corresponding API key to `.env` for whichever provider you choose.

### Modifying agent behaviour

| File | What to change |
|---|---|
| `src/ai_travel_assistant/config/agents.yaml` | Role, goal, and backstory for the 3 itinerary crew agents |
| `src/ai_travel_assistant/config/tasks.yaml` | Task instructions and expected outputs for the itinerary crew |
| `src/ai_travel_assistant/crew.py` | Tools, LLM settings, and task context wiring for the itinerary crew |
| `src/ai_travel_assistant/flight_flow.py` | Flight agent role/goal/backstory, prompt, and LLM settings |

---

## Future Work

1. Include advanced reasoning, planning, collaboration, and state memory into agents for more complex and detailed itinerary planning
2. Infrastructure & deployment: Docker containerisation, observability, and evaluation
