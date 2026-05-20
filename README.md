# AI Travel Itinerary Planner Assistant

A multi-agent AI travel planner built with [crewAI](https://crewai.com). Given a trip request, three specialised agents collaborate sequentially to research every destination, gather local insider knowledge, and produce a complete day-by-day itinerary across destinations based on your travel style.

## Architecture

### Agent Pipeline

Three agents run in sequence. Each agent's output is passed as context to the next.

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
│  Itinerary Writer   │
│                     │
│                     │  • Builds day-by-day schedule in destination blocks
│                     │  • Honours the day-distribution table from Travel Researcher
│                     │  • Labels transit days between destinations explicitly
│                     │  → outputs/suggested_itinerary.md
└─────────────────────┘
```

### Day Distribution Logic

The Travel Researcher decides how to split the trip duration across multiple destinations using these rules:

| Travel Style | Behaviour |
|---|---|
| `relax` | Depth over breadth: more days per destination, fewer moves |
| `adventure` | More stops, shorter stays, optimised for variety |
| `business` | Anchors around business commitments first, fills gaps with sightseeing |

Transit time between destinations is always accounted for (minimum half a day).

### Input Data

Defined as `TravelRequest` in `src/ai_travel_assistant/crew.py`:

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

### Output Files

Both outputs are written to the `outputs/` directory:

| File | Produced by | Contents |
|---|---|---|
| `outputs/recommended_insights.md` | Local Guide | Per-destination insider guide scaled to days allocated |
| `outputs/suggested_itinerary.md` | Itinerary Writer | Full day-by-day schedule with accommodation, dining, transport, and budget breakdown |

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
# LLM provider: project uses Groq by default
# You may use other proprietary model providers as needed
GROQ_API_KEY=your_groq_api_key

# Web search tool used by Travel Researcher and Local Guide
SERPER_API_KEY=your_serper_api_key
```

Get your Groq and Serper API keys here:
- **Groq**: [console.groq.com](https://console.groq.com) (free tier available)
- **Serper**: [serper.dev](https://serper.dev) (free tier: 2,500 searches)

### 3. Run

**Streamlit UI (recommended)**

```bash
uv run streamlit run app.py
```

Opens at `http://localhost:8501`. Fill in the form and click **Plan My Trip**.

**CLI**

```bash
crewai run
```

Edit `_SAMPLE_REQUEST` in `main.py` to change the trip inputs.

Outputs are written to `outputs/recommended_insights.md` and `outputs/suggested_itinerary.md`.

---

## Configuration

### Changing the travel request

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

All three agents are configured in `src/ai_travel_assistant/config/agents.yaml`. The `llm` field on each agent controls the model:

```yaml
travel_expert:
  llm: groq/llama-3.3-70b-versatile   # change this line
  ...
```

Any [LiteLLM-supported provider](https://docs.litellm.ai/docs/providers) can be used with the format `provider/model-name`:

```yaml
llm: anthropic/claude-sonnet-4-20250514
llm: openai/gpt-4o
llm: groq/llama-3.3-70b-versatile
```

Add the corresponding API key to `.env` for whichever provider you choose.

### Modifying agent behaviour

| File | What to change |
|---|---|
| `src/ai_travel_assistant/config/agents.yaml` | Agent role, goal, backstory, and LLM model |
| `src/ai_travel_assistant/config/tasks.yaml` | Task instructions and expected outputs |
| `src/ai_travel_assistant/crew.py` | Tools assigned to each agent, task context wiring |


### Future Work
1. Set up knowledge base of flight prices and details for improved planning
2. Include advanced Reasoning, Planning, Collaboration and State Memory into agents for more complex and detailed itinerary planning
3. Infrastructure & Deployment using Docker Containerization, observability and evaluation


