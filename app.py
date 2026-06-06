import os
import re
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from ai_travel_assistant.crew import AiTravelAssistant, TravelRequest
from ai_travel_assistant.flight_flow import FlightRequest, FlightSearchFlow

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

OUTPUT_FLIGHTS = "outputs/flight_options.md"
OUTPUT_INSIGHTS = "outputs/recommended_insights.md"
OUTPUT_ITINERARY = "outputs/suggested_itinerary.md"


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_destinations(raw: str) -> list[str]:
    return [d.strip() for d in raw.split(",") if d.strip()]


FLIGHT_COLUMNS = [
    "Flight No.",
    "Date",
    "Dep. Time",
    "Arr. Time",
    "Journey Time",
    "Stops",
    "Price",
    "Airline",
    "Departure Airport",
    "Arrival Airport",
]


def parse_flight_section(text: str, section: str) -> pd.DataFrame | None:
    """Extract a numbered flight list from one section and return as a DataFrame."""
    pattern = rf"##\s*{re.escape(section)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    rows = []
    for line in match.group(1).strip().splitlines():
        line = line.strip()
        # Match lines starting with a number: "1. ..." or "1) ..."
        if not re.match(r"^\d+[.)]\s", line):
            continue
        # Strip the leading number
        line = re.sub(r"^\d+[.)]\s*", "", line)
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 10:
            rows.append(parts[:10])

    if not rows:
        return None
    return pd.DataFrame(rows, columns=FLIGHT_COLUMNS)


def render_flight_results(flights_text: str) -> None:
    for section in ("Outbound Flights", "Return Flights"):
        st.markdown(f"### {section}")
        df = parse_flight_section(flights_text, section)
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            # Fallback: render as plain markdown if parsing fails
            st.markdown(flights_text)
            break


def read_output(path: str) -> str | None:
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return None


def run_itinerary(request: TravelRequest) -> tuple[str | None, str | None]:
    """Run the itinerary crew and return (insights_md, itinerary_md)."""
    os.makedirs("outputs", exist_ok=True)
    AiTravelAssistant().crew().kickoff(inputs=request.to_crew_inputs())
    return read_output(OUTPUT_INSIGHTS), read_output(OUTPUT_ITINERARY)


def run_flight_search(request: FlightRequest) -> str | None:
    """Run the flight search flow and return flights_md."""
    FlightSearchFlow().kickoff(inputs=request.to_flow_inputs())
    return read_output(OUTPUT_FLIGHTS)


# ── Session state init ────────────────────────────────────────────────────────
for key in ("flights", "insights", "itinerary", "error"):
    if key not in st.session_state:
        st.session_state[key] = None


# ── Header ────────────────────────────────────────────────────────────────────
st.title("✈️ AI Travel Assistant")
st.caption(
    "Choose a mode: **Plan Itinerary** uses three AI agents to research your destinations, "
    "gather local insights, and build a day-by-day itinerary. "
    "**Find Flights** uses a dedicated flight agent to search for the best deals."
)
st.caption(
    "⚠️ Outputs are AI-generated suggestions. Please review itineraries, local insights, "
    "and flight options before booking. Verify prices, availability, and details directly "
    "with airlines or travel providers."
)
st.divider()


# ── Mode selector ─────────────────────────────────────────────────────────────
mode = st.radio(
    "Mode",
    ["🗺️ Plan Itinerary", "✈️ Find Flights"],
    horizontal=True,
    label_visibility="collapsed",
)
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# MODE: Plan Itinerary
# ══════════════════════════════════════════════════════════════════════════════
if mode == "🗺️ Plan Itinerary":

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

        submitted = st.form_submit_button(
            "🗺️ Plan My Trip", use_container_width=True, type="primary"
        )

    if submitted:
        st.session_state.insights = None
        st.session_state.itinerary = None
        st.session_state.error = None

        destinations = parse_destinations(destinations_raw)

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
                f"This takes a few minutes while agents are working…"
            )

            with st.spinner(
                "Agents are researching destinations, gathering local insights, and writing your itinerary…"
            ):
                try:
                    insights, itinerary = run_itinerary(request)
                    st.session_state.insights = insights
                    st.session_state.itinerary = itinerary
                    st.success("Done! Your travel plan is ready.")
                except Exception as e:
                    st.session_state.error = str(e)

    if st.session_state.error:
        st.error(f"The crew encountered an error:\n\n{st.session_state.error}")

    if st.session_state.insights or st.session_state.itinerary:
        st.divider()
        st.subheader("Your Travel Plan")

        tab_itinerary, tab_insights = st.tabs(
            ["📅 Full Itinerary", "📍 Local Insights"]
        )

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


# ══════════════════════════════════════════════════════════════════════════════
# MODE: Find Flights
# ══════════════════════════════════════════════════════════════════════════════
else:

    with st.form("flight_form"):
        st.subheader("Flight Search")

        col1, col2 = st.columns(2)
        with col1:
            fl_origin = st.text_input(
                "Origin city / country",
                value="Singapore",
                placeholder="e.g. Singapore",
            )
        with col2:
            fl_destinations_raw = st.text_input(
                "Destinations (comma-separated)",
                value="Tokyo",
                placeholder="e.g. Tokyo, Osaka",
            )

        col3, col4 = st.columns(2)
        with col3:
            fl_start_date = st.date_input(
                "Departure date",
                value=date.today() + timedelta(days=30),
                min_value=date.today(),
                key="fl_start",
            )
        with col4:
            fl_end_date = st.date_input(
                "Return date",
                value=date.today() + timedelta(days=39),
                min_value=date.today() + timedelta(days=1),
                key="fl_end",
            )

        fl_currency = st.selectbox(
            "Currency for price display",
            options=["SGD", "USD", "EUR", "GBP", "JPY", "AUD", "MYR"],
            index=0,
            key="fl_currency",
        )

        fl_submitted = st.form_submit_button(
            "✈️ Find Flights", use_container_width=True, type="primary"
        )

    if fl_submitted:
        st.session_state.flights = None
        st.session_state.error = None

        fl_destinations = parse_destinations(fl_destinations_raw)

        errors = []
        if not fl_origin.strip():
            errors.append("Origin is required.")
        if not fl_destinations:
            errors.append("At least one destination is required.")
        if fl_end_date <= fl_start_date:
            errors.append("Return date must be after departure date.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            flight_request = FlightRequest(
                origin=fl_origin.strip(),
                destinations=fl_destinations,
                start_date=fl_start_date,
                end_date=fl_end_date,
                currency=fl_currency,
            )

            st.info(
                f"Searching flights from **{fl_origin}** to **{', '.join(fl_destinations)}** "
                f"departing **{fl_start_date}**, returning **{fl_end_date}** ({fl_currency}). "
                f"This takes a minute…"
            )

            with st.spinner("Flight agent is searching for the best deals…"):
                try:
                    flights = run_flight_search(flight_request)
                    st.session_state.flights = flights
                    st.success("Done! Flight options are ready.")
                except Exception as e:
                    st.session_state.error = str(e)

    if st.session_state.error:
        st.error(f"The crew encountered an error:\n\n{st.session_state.error}")

    if st.session_state.flights:
        st.divider()
        st.subheader("Flight Options")
        render_flight_results(st.session_state.flights)
        st.download_button(
            label="Download Flight Options",
            data=st.session_state.flights,
            file_name="flight_options.md",
            mime="text/markdown",
        )
