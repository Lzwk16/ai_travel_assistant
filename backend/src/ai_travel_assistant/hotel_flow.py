"""Hotel search flow — deterministic, no LLM in the data path.

 Hotel search needs no reasoning — the cities are given — so the flow now calls the
tool directly, ranks deterministically, and formats from the real
``HotelOption`` data. The output is therefore exactly what Google Hotels
returned.
"""

from datetime import date

from crewai.flow.flow import Flow, start
from pydantic import BaseModel, Field, model_validator

from ai_travel_assistant.config import HOTEL_OPTIONS_FILE, ensure_outputs_dir
from ai_travel_assistant.tools.google_hotels import GoogleHotelsTool, HotelOption

# Hotels presented per city.
TOP_N = 5

# Ranking weights (best value, not just cheapest): nightly price, guest rating,
# star class. Mirrors the heuristic the agent used to be told to apply.
_W_PRICE, _W_RATING, _W_STARS = 0.4, 0.4, 0.2


class HotelRequest(BaseModel):
    destinations: list[str] = Field(
        description="List of cities to find hotels in",
        examples=["Tokyo", "Kyoto"],
        min_length=1,
    )
    start_date: date = Field(description="Check-in date", examples=["2025-06-01"])
    end_date: date = Field(description="Check-out date", examples=["2025-06-10"])
    currency: str = Field(
        default="SGD",
        description="Currency for price display",
        examples=["SGD", "USD", "JPY"],
    )
    adults: int = Field(
        default=2, ge=1, description="Number of adult guests", examples=[2]
    )
    children: int = Field(
        default=0, ge=0, description="Number of children", examples=[0, 1]
    )

    @model_validator(mode="after")
    def check_date_order(self) -> "HotelRequest":
        if self.end_date <= self.start_date:
            raise ValueError("end_date (check-out) must be after start_date (check-in)")
        return self

    def to_flow_inputs(self) -> dict:
        return {
            "destinations": self.destinations,
            "check_in_date": self.start_date.strftime("%Y-%m-%d"),
            "check_out_date": self.end_date.strftime("%Y-%m-%d"),
            "currency": self.currency,
            "adults": self.adults,
            "children": self.children,
        }


def _rank(options: list[dict], top_n: int) -> list[dict]:
    """Rank raw SerpAPI properties by best value and return the top ``top_n``.

    Score = weighted sum of price (lower better, min-max normalised within the
    returned set), guest rating (/5), and star class (/5). Missing fields score
    0 for that component, so under-described listings sink rather than error.
    """
    usable = [r for r in options if r.get("name")]
    prices = [
        p
        for r in usable
        if isinstance(
            p := (r.get("rate_per_night") or {}).get("extracted_lowest"), (int, float)
        )
    ]
    pmin, pmax = (min(prices), max(prices)) if prices else (None, None)

    def score(r: dict) -> float:
        price = (r.get("rate_per_night") or {}).get("extracted_lowest")
        if isinstance(price, (int, float)) and pmin is not None and pmax > pmin:
            price_s = 1 - (price - pmin) / (pmax - pmin)
        elif isinstance(price, (int, float)):
            price_s = 1.0  # all same price, or a single priced option
        else:
            price_s = 0.0
        rating = r.get("overall_rating")
        rating_s = rating / 5 if isinstance(rating, (int, float)) else 0.0
        stars = r.get("extracted_hotel_class")
        star_s = stars / 5 if isinstance(stars, (int, float)) else 0.0
        return _W_PRICE * price_s + _W_RATING * rating_s + _W_STARS * star_s

    return sorted(usable, key=score, reverse=True)[:top_n]


def _format_city(city: str, ranked: list[dict], currency: str) -> str:
    lines = [f"## Hotels in {city}"]
    rank = 0
    for raw in ranked:
        option = HotelOption.from_api_property(raw)
        if option is None:
            continue
        rank += 1
        lines.append(
            f"{rank}. {option.name} | {city} | {option.hotel_class} | "
            f"{option.rating} ({option.reviews} reviews) | "
            f"{option.price_per_night} {currency}/night | "
            f"{option.total_price} {currency} | {option.amenities}"
        )
    if rank == 0:
        lines.append("No hotels found.")
    return "\n".join(lines)


class HotelSearchFlow(Flow):
    @start()
    def search_hotels(self) -> str:
        destinations = self.state["destinations"]
        check_in_date = self.state["check_in_date"]
        check_out_date = self.state["check_out_date"]
        currency = self.state["currency"]
        adults = self.state["adults"]
        children = self.state["children"]

        tool = GoogleHotelsTool(adults=adults, children=children)
        sections = []
        for city in destinations:
            options = tool.search(city, check_in_date, check_out_date, currency)
            sections.append(_format_city(city, _rank(options, TOP_N), currency))

        markdown = "\n\n".join(sections)
        ensure_outputs_dir()
        with open(HOTEL_OPTIONS_FILE, "w", encoding="utf-8") as f:
            f.write(markdown)
        return markdown
