import os
from dataclasses import dataclass

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from serpapi import GoogleSearch

# Cap on options returned to the agent — keeps tool output within the LLM's
# context budget while leaving enough candidates for ranking.
MAX_AGENT_RESULTS = 5

# Default age used for each child when the request specifies children but not
# their individual ages. Google Hotels requires an age per child; expose
# per-child ages on the request model later if finer control is needed.
_DEFAULT_CHILD_AGE = 10


class HotelSearchInput(BaseModel):
    location: str = Field(
        description="City or area to search hotels in (e.g. 'Tokyo', 'Kyoto', "
        "'Osaka'). Use a plain place name as you would in Google Hotels."
    )
    check_in_date: str = Field(description="Check-in date in YYYY-MM-DD format")
    check_out_date: str = Field(description="Check-out date in YYYY-MM-DD format")
    currency: str = Field(
        default="SGD", description="Currency code (e.g. SGD, USD, JPY)"
    )


@dataclass
class HotelOption:
    """Display-ready fields extracted from one SerpAPI hotel property."""

    name: str
    hotel_class: str
    rating: str | float
    reviews: str | int
    price_per_night: str | int
    total_price: str | int
    amenities: str

    @classmethod
    def from_api_property(cls, prop: dict) -> "HotelOption | None":
        """Parse one SerpAPI 'properties' entry; None if it has no name."""
        name = prop.get("name")
        if not name:
            return None

        star = prop.get("extracted_hotel_class")
        hotel_class = f"{star}-star" if star else (prop.get("hotel_class") or "?")

        rate = prop.get("rate_per_night") or {}
        total = prop.get("total_rate") or {}
        price_per_night = rate.get("extracted_lowest") or rate.get("lowest") or "?"
        total_price = total.get("extracted_lowest") or total.get("lowest") or "?"

        amenities_list = prop.get("amenities") or []
        amenities = ", ".join(amenities_list[:3]) if amenities_list else "—"

        return cls(
            name=name,
            hotel_class=hotel_class,
            rating=prop.get("overall_rating", "?"),
            reviews=prop.get("reviews", "?"),
            price_per_night=price_per_night,
            total_price=total_price,
            amenities=amenities,
        )


class GoogleHotelsTool(BaseTool):
    name: str = "Google Hotels Search"
    description: str = (
        "Fetches real hotel data from Google Hotels via SerpAPI. "
        "Returns verified hotel names, star class, guest ratings, nightly and "
        "total-stay prices, and amenities for a city across a date range. "
        "Supply a plain city/area name as the location (e.g. 'Tokyo', 'Kyoto') "
        "and check-in/check-out dates in YYYY-MM-DD format. Each call searches "
        "one location only; call once per destination city."
    )
    args_schema: type[BaseModel] = HotelSearchInput

    # Guest counts, set per request when the flow builds the tool. Kept as
    # tool-instance config and OUT of HotelSearchInput on purpose: Groq coerces
    # integer tool-schema fields to strings, which breaks the agent's tool-call
    # validation. Default to the Google Hotels API's own defaults (2 adults, 0
    # children) for direct/standalone use.
    adults: int = 2
    children: int = 0

    # ── public entry point (used directly by the flow) ────────────────────────

    def search(
        self,
        location: str,
        check_in_date: str,
        check_out_date: str,
        currency: str = "SGD",
    ) -> list[dict]:
        """Return raw property dicts from Google Hotels. Empty list on failure."""
        api_key = os.getenv("SERP_API_KEY")
        if not api_key:
            return []
        raw = self._fetch(location, check_in_date, check_out_date, currency, api_key)
        if isinstance(raw, str):
            return []
        return raw.get("properties") or []

    # ── crewai BaseTool entry point (used by agent) ───────────────────────────

    def _run(
        self,
        location: str,
        check_in_date: str,
        check_out_date: str,
        currency: str = "SGD",
    ) -> str:
        options = self.search(location, check_in_date, check_out_date, currency)
        if not options:
            return (
                f"No hotels found for {location} "
                f"({check_in_date} → {check_out_date})."
            )
        return self._format_for_agent(
            options[:MAX_AGENT_RESULTS],
            location,
            check_in_date,
            check_out_date,
            currency,
        )

    def _format_for_agent(
        self,
        options: list,
        location: str,
        check_in_date: str,
        check_out_date: str,
        currency: str,
    ) -> str:
        """Simple numbered list — easy for the agent to reproduce verbatim."""
        lines = [
            f"Hotels in {location} ({check_in_date} → {check_out_date}, {currency}):"
        ]

        for idx, raw_option in enumerate(options, 1):
            option = HotelOption.from_api_property(raw_option)
            if option is None:
                continue
            lines.append(
                f"{idx}. {option.name} | {location} | {option.hotel_class} | "
                f"{option.rating} ({option.reviews} reviews) | "
                f"{option.price_per_night} {currency}/night | "
                f"{option.total_price} {currency} total | {option.amenities}"
            )

        return "\n".join(lines)

    # ── formatting (called by flow after merging multi-city results) ──────────

    @staticmethod
    def format_table(
        options: list[dict],
        location: str,
        check_in_date: str,
        check_out_date: str,
        currency: str,
    ) -> str:
        lines = [
            f"### {location} ({check_in_date} → {check_out_date}, {currency})\n",
            f"| # | Hotel | Class | Rating | Reviews | Price/Night ({currency}) "
            f"| Total ({currency}) | Amenities |",
            "|---|---|---|---|---|---|---|---|",
        ]

        for idx, raw_option in enumerate(options, 1):
            option = HotelOption.from_api_property(raw_option)
            if option is None:
                continue
            lines.append(
                f"| {idx} | {option.name} | {option.hotel_class} | {option.rating} "
                f"| {option.reviews} | {option.price_per_night} "
                f"| {option.total_price} | {option.amenities} |"
            )

        return "\n".join(lines)

    # ── private helpers ───────────────────────────────────────────────────────

    def _fetch(
        self,
        location: str,
        check_in_date: str,
        check_out_date: str,
        currency: str,
        api_key: str,
    ) -> dict | str:
        params = {
            "engine": "google_hotels",
            "q": location,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "currency": currency,
            "hl": "en",
            "adults": self.adults,
            "api_key": api_key,
        }
        if self.children > 0:
            # Google Hotels needs an age per child; default each to a typical
            # mid-childhood age (see _DEFAULT_CHILD_AGE).
            params["children"] = self.children
            params["children_ages"] = ",".join(
                str(_DEFAULT_CHILD_AGE) for _ in range(self.children)
            )
        try:
            result = GoogleSearch(params).get_dict()

            if "error" in result:
                return f"SerpAPI error: {result['error']}"

            return result

        except Exception as exc:
            return f"Request failed: {exc}"
