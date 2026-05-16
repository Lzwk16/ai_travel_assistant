import os
import streamlit as st
from datetime import date, timedelta

from ai_travel_assistant.crew import AiTravelAssistant, TravelRequest

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Travel Assistant",
    page_icon="✈️",
    layout="wide",
)

# ── Constants ─────────────────────────────────────────────────────────────────
INTERESTS_OPTIONS = [
    "Food & dining",
    "Local culture",
    "Sightseeing & landmarks",
    "Nature & outdoors",
    "Shopping",
    "Nightlife",
    "Art & museums",
    "Adventure sports",
    "Wellness & spa",
    "History",
]

OUTPUT_INSIGHTS = "outputs/recommended_insights.md"
OUTPUT_ITINERARY = "outputs/suggested_itinerary.md"


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_destinations(raw: str) -> list[str]:
    return [d.strip() for d in raw.split(",") if d.strip()]


def read_output(path: str) -> str | None:
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return None


def run_crew(request: TravelRequest) -> tuple[str | None, str | None]:
    """Run the crew and return (insights_md, itinerary_md)."""
    os.makedirs("outputs", exist_ok=True)
    AiTravelAssistant().crew().kickoff(inputs=request.to_crew_inputs())
    return read_output(OUTPUT_INSIGHTS), read_output(OUTPUT_ITINERARY)


# ── Session state init ────────────────────────────────────────────────────────
if "insights" not in st.session_state:
    st.session_state.insights = None
if "itinerary" not in st.session_state:
    st.session_state.itinerary = None
if "error" not in st.session_state:
    st.session_state.error = None


# ── Header ────────────────────────────────────────────────────────────────────
st.title("✈️ AI Travel Assistant")
st.caption(
    "Three AI agents collaborate to research your destinations, gather local insights, "
    "and build a day-by-day itinerary — with smart day distribution based on your travel style."
)
st.divider()


# ── Input form ────────────────────────────────────────────────────────────────
with st.form("trip_form"):
    st.subheader("Trip Details")

    col1, col2 = st.columns(2)
    with col1:
        origin = st.text_input(
            "Origin city / country",
            value="Singapore",
            placeholder="e.g. Singapore",
        )
    with col2:
        destinations_raw = st.text_input(
            "Destinations (comma-separated)",
            value="Tokyo, Osaka",
            placeholder="e.g. Tokyo, Osaka, Kyoto",
        )

    col3, col4 = st.columns(2)
    with col3:
        start_date = st.date_input(
            "Start date",
            value=date.today() + timedelta(days=30),
            min_value=date.today(),
        )
    with col4:
        end_date = st.date_input(
            "End date",
            value=date.today() + timedelta(days=39),
            min_value=date.today() + timedelta(days=1),
        )

    col5, col6 = st.columns(2)
    with col5:
        group_size = st.number_input(
            "Group size",
            min_value=1,
            max_value=20,
            value=2,
        )
    with col6:
        budget_type = st.selectbox(
            "Budget",
            options=["budget", "mid-range", "luxury"],
            index=1,
        )

    col7, col8 = st.columns(2)
    with col7:
        travel_style = st.selectbox(
            "Travel style",
            options=["relax", "adventure", "business"],
            help=(
                "relax → depth over breadth, fewer moves | "
                "adventure → more stops, faster pace | "
                "business → schedule anchored to commitments"
            ),
        )
    with col8:
        currency = st.selectbox(
            "Currency for cost estimates",
            options=["SGD", "USD", "EUR", "GBP", "JPY", "AUD", "MYR"],
            index=0,
        )

    interests = st.multiselect(
        "Interests",
        options=INTERESTS_OPTIONS,
        default=["Food & dining", "Local culture", "Sightseeing & landmarks"],
    )

    submitted = st.form_submit_button("🗺️ Plan My Trip", use_container_width=True, type="primary")


# ── Validation & execution ────────────────────────────────────────────────────
if submitted:
    st.session_state.insights = None
    st.session_state.itinerary = None
    st.session_state.error = None

    destinations = parse_destinations(destinations_raw)

    # Client-side validation
    errors = []
    if not origin.strip():
        errors.append("Origin is required.")
    if not destinations:
        errors.append("At least one destination is required.")
    if end_date <= start_date:
        errors.append("End date must be after start date.")
    if not interests:
        errors.append("Select at least one interest.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        request = TravelRequest(
            origin=origin.strip(),
            destinations=destinations,
            start_date=start_date,
            end_date=end_date,
            group_size=int(group_size),
            budget_type=budget_type,
            interests=interests,
            travel_style=travel_style,
            currency=currency,
        )

        duration_days = (end_date - start_date).days
        st.info(
            f"Planning a **{duration_days}-day {travel_style}** trip for **{group_size}** "
            f"from **{origin}** to **{', '.join(destinations)}** ({currency}). "
            f"This takes a few minutes — agents are working…"
        )

        with st.spinner("Agents are researching, gathering local insights, and writing your itinerary…"):
            try:
                insights, itinerary = run_crew(request)
                st.session_state.insights = insights
                st.session_state.itinerary = itinerary
                st.success("Done! Your travel plan is ready.")
            except Exception as e:
                st.session_state.error = str(e)


# ── Error display ─────────────────────────────────────────────────────────────
if st.session_state.error:
    st.error(f"The crew encountered an error:\n\n{st.session_state.error}")


# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.insights or st.session_state.itinerary:
    st.divider()
    st.subheader("Your Travel Plan")

    tab_itinerary, tab_insights = st.tabs(["📅 Full Itinerary", "📍 Local Insights"])

    with tab_itinerary:
        if st.session_state.itinerary:
            st.markdown(st.session_state.itinerary)
            st.download_button(
                label="Download Itinerary",
                data=st.session_state.itinerary,
                file_name="itinerary.md",
                mime="text/markdown",
            )
        else:
            st.warning("Itinerary output not found.")

    with tab_insights:
        if st.session_state.insights:
            st.markdown(st.session_state.insights)
            st.download_button(
                label="Download Local Insights",
                data=st.session_state.insights,
                file_name="local_insights.md",
                mime="text/markdown",
            )
        else:
            st.warning("Local insights output not found.")
