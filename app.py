import os
from datetime import date, timedelta

import streamlit as st

from ai_travel_assistant.config import (
    FLIGHT_OPTIONS_FILE,
    INSIGHTS_FILE,
    ITINERARY_FILE,
    ensure_outputs_dir,
)
from ai_travel_assistant.crew import AiTravelAssistant, TravelRequest
from ai_travel_assistant.flight_flow import FlightRequest, FlightSearchFlow
from ai_travel_assistant.flight_results import parse_flight_section

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

CURRENCY_OPTIONS = ["SGD", "USD", "EUR", "GBP", "JPY", "AUD", "MYR"]

DEFAULT_START_OFFSET = timedelta(days=30)
DEFAULT_END_OFFSET = timedelta(days=39)


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_destinations(raw: str) -> list[str]:
    return [d.strip() for d in raw.split(",") if d.strip()]


def validate_trip_form(
    origin: str,
    destinations: list[str],
    start_date: date,
    end_date: date,
    date_error: str,
    interests: list[str] | None = None,
) -> list[str]:
    """Return human-readable validation errors; empty list means the form is valid."""
    errors = []
    if not origin.strip():
        errors.append("Origin is required.")
    if not destinations:
        errors.append("At least one destination is required.")
    if end_date <= start_date:
        errors.append(date_error)
    if interests is not None and not interests:
        errors.append("Select at least one interest.")
    return errors


def show_errors(errors: list[str]) -> None:
    for error in errors:
        st.error(error)


def show_crew_error() -> None:
    if st.session_state.error:
        st.error(f"The crew encountered an error:\n\n{st.session_state.error}")


def markdown_download_button(label: str, content: str, file_name: str) -> None:
    st.download_button(
        label=label,
        data=content,
        file_name=file_name,
        mime="text/markdown",
    )


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
    ensure_outputs_dir()
    AiTravelAssistant().crew().kickoff(inputs=request.to_crew_inputs())
    return read_output(INSIGHTS_FILE), read_output(ITINERARY_FILE)


def run_flight_search(request: FlightRequest) -> str | None:
    """Run the flight search flow and return flights_md."""
    FlightSearchFlow().kickoff(inputs=request.to_flow_inputs())
    return read_output(FLIGHT_OPTIONS_FILE)


# ══════════════════════════════════════════════════════════════════════════════
# MODE: Plan Itinerary
# ══════════════════════════════════════════════════════════════════════════════
def render_itinerary_mode() -> None:
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
                value=date.today() + DEFAULT_START_OFFSET,
                min_value=date.today(),
            )
        with col4:
            end_date = st.date_input(
                "End date",
                value=date.today() + DEFAULT_END_OFFSET,
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
                options=CURRENCY_OPTIONS,
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

        errors = validate_trip_form(
            origin,
            destinations,
            start_date,
            end_date,
            date_error="End date must be after start date.",
            interests=interests,
        )

        if errors:
            show_errors(errors)
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
                f"Planning a **{duration_days}-day {travel_style}** trip "
                f"for **{group_size}** "
                f"from **{origin}** to **{', '.join(destinations)}** ({currency}). "
                f"This takes a few minutes while agents are working…"
            )

            with st.spinner(
                "Agents are researching destinations, gathering local insights, "
                "and writing your itinerary…"
            ):
                try:
                    insights, itinerary = run_itinerary(request)
                    st.session_state.insights = insights
                    st.session_state.itinerary = itinerary
                    st.success("Done! Your travel plan is ready.")
                except Exception as e:
                    st.session_state.error = str(e)

    show_crew_error()

    if st.session_state.insights or st.session_state.itinerary:
        st.divider()
        st.subheader("Your Travel Plan")

        tab_itinerary, tab_insights = st.tabs(
            ["📅 Full Itinerary", "📍 Local Insights"]
        )

        with tab_itinerary:
            if st.session_state.itinerary:
                st.markdown(st.session_state.itinerary)
                markdown_download_button(
                    "Download Itinerary", st.session_state.itinerary, "itinerary.md"
                )
            else:
                st.warning("Itinerary output not found.")

        with tab_insights:
            if st.session_state.insights:
                st.markdown(st.session_state.insights)
                markdown_download_button(
                    "Download Local Insights",
                    st.session_state.insights,
                    "local_insights.md",
                )
            else:
                st.warning("Local insights output not found.")


# ══════════════════════════════════════════════════════════════════════════════
# MODE: Find Flights
# ══════════════════════════════════════════════════════════════════════════════
def render_flights_mode() -> None:
    with st.form("flight_form"):
        st.subheader("Flight Search")

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
                value="Tokyo",
                placeholder="e.g. Tokyo, Osaka",
            )

        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input(
                "Departure date",
                value=date.today() + DEFAULT_START_OFFSET,
                min_value=date.today(),
                key="fl_start",
            )
        with col4:
            end_date = st.date_input(
                "Return date",
                value=date.today() + DEFAULT_END_OFFSET,
                min_value=date.today() + timedelta(days=1),
                key="fl_end",
            )

        currency = st.selectbox(
            "Currency for price display",
            options=CURRENCY_OPTIONS,
            index=0,
            key="fl_currency",
        )

        submitted = st.form_submit_button(
            "✈️ Find Flights", use_container_width=True, type="primary"
        )

    if submitted:
        st.session_state.flights = None
        st.session_state.error = None

        destinations = parse_destinations(destinations_raw)

        errors = validate_trip_form(
            origin,
            destinations,
            start_date,
            end_date,
            date_error="Return date must be after departure date.",
        )

        if errors:
            show_errors(errors)
        else:
            flight_request = FlightRequest(
                origin=origin.strip(),
                destinations=destinations,
                start_date=start_date,
                end_date=end_date,
                currency=currency,
            )

            st.info(
                f"Searching flights from **{origin}** to **{', '.join(destinations)}** "
                f"departing **{start_date}**, returning **{end_date}** ({currency}). "
                f"This takes a minute…"
            )

            with st.spinner("Flight agent is searching for the best deals…"):
                try:
                    flights = run_flight_search(flight_request)
                    st.session_state.flights = flights
                    st.success("Done! Flight options are ready.")
                except Exception as e:
                    st.session_state.error = str(e)

    show_crew_error()

    if st.session_state.flights:
        st.divider()
        st.subheader("Flight Options")
        render_flight_results(st.session_state.flights)
        markdown_download_button(
            "Download Flight Options", st.session_state.flights, "flight_options.md"
        )


# ── Session state init ────────────────────────────────────────────────────────
for key in ("flights", "insights", "itinerary", "error"):
    if key not in st.session_state:
        st.session_state[key] = None


# ── Header ────────────────────────────────────────────────────────────────────
st.title("✈️ AI Travel Assistant")
st.caption(
    "Choose a mode: **Plan Itinerary** uses three AI agents to research your "
    "destinations, gather local insights, and build a day-by-day itinerary. "
    "**Find Flights** uses a dedicated flight agent to search for the best deals."
)
st.caption(
    "⚠️ Outputs are AI-generated suggestions. Please review itineraries, local "
    "insights, and flight options before booking. Verify prices, availability, "
    "and details directly with airlines or travel providers."
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

if mode == "🗺️ Plan Itinerary":
    render_itinerary_mode()
else:
    render_flights_mode()
