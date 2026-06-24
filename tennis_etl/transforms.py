"""Flatten SportRadar Tennis JSON payloads into relational rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

JsonObject = Mapping[str, Any]


def _normalize_name(name: str | None) -> str | None:
    """
    Convert "Last, First" (SportRadar format) to "First Last".
    Leaves names that contain no comma unchanged.
    """
    if not name:
        return name
    if "," in name:
        parts = name.split(",", 1)
        first = parts[1].strip()
        last = parts[0].strip()
        return f"{first} {last}"
    return name


def transform_competitions(
    payload: JsonObject,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return category and competition rows from the competitions payload."""
    categories: dict[str, dict[str, Any]] = {}
    competitions: dict[str, dict[str, Any]] = {}

    for competition in _items(payload, "competitions"):
        category = competition.get("category") or {}
        category_id = category.get("id") or competition.get("category_id")
        competition_id = competition.get("id")
        if not competition_id or not category_id:
            continue

        categories[category_id] = {
            "category_id": category_id,
            "category_name": category.get("name")
            or competition.get("category_name")
            or "Unknown",
        }
        competitions[competition_id] = {
            "competition_id": competition_id,
            "competition_name": competition.get("name") or "Unknown",
            "parent_id": _parent_id(competition.get("parent")),
            "type": competition.get("type"),
            "gender": competition.get("gender"),
            "category_id": category_id,
        }

    return list(categories.values()), list(competitions.values())


def transform_complexes(
    payload: JsonObject,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return complex and nested venue rows from the complexes payload."""
    complexes: dict[str, dict[str, Any]] = {}
    venues: dict[str, dict[str, Any]] = {}

    for complex_item in _items(payload, "complexes"):
        complex_id = complex_item.get("id")
        if not complex_id:
            continue

        complexes[complex_id] = {
            "complex_id": complex_id,
            "complex_name": complex_item.get("name") or "Unknown",
        }
        for venue in _nested_items(complex_item, "venues"):
            venue_id = venue.get("id")
            if not venue_id:
                continue
            venues[venue_id] = {
                "venue_id": venue_id,
                "venue_name": venue.get("name") or "Unknown",
                "city_name": venue.get("city_name"),
                "country_name": venue.get("country_name"),
                "country_code": venue.get("country_code"),
                "timezone": venue.get("timezone"),
                "complex_id": complex_id,
            }

    return list(complexes.values()), list(venues.values())


def transform_doubles_rankings(
    payload: JsonObject,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return competitor and current ranking rows from ranking groups."""
    competitors: dict[str, dict[str, Any]] = {}
    rankings: dict[str, dict[str, Any]] = {}

    for ranking_group in _ranking_groups(payload):
        gender = ranking_group.get("gender")
        for item in _nested_items(ranking_group, "competitor_rankings"):
            competitor = item.get("competitor") or {}
            competitor_id = competitor.get("id")
            rank = _as_int(item.get("rank"))
            if not competitor_id or rank is None:
                continue

            competitors[competitor_id] = {
                "competitor_id": competitor_id,
                "name": _normalize_name(competitor.get("name")) or "Unknown",
                "country": competitor.get("country"),
                "country_code": competitor.get("country_code"),
                "abbreviation": competitor.get("abbreviation"),
                "gender": gender,
            }
            rankings[competitor_id] = {
                "rank": rank,
                "movement": _as_int(item.get("movement")),
                "points": _as_int(item.get("points")),
                "competitions_played": _as_int(item.get("competitions_played")),
                "competitor_id": competitor_id,
            }

    return list(competitors.values()), list(rankings.values())


def _items(payload: JsonObject, key: str) -> Iterable[JsonObject]:
    value = payload.get(key, [])
    return value if isinstance(value, list) else []


def _nested_items(payload: JsonObject, key: str) -> Iterable[JsonObject]:
    value = payload.get(key, [])
    return value if isinstance(value, list) else []


def _ranking_groups(payload: JsonObject) -> Iterable[JsonObject]:
    rankings = payload.get("rankings")
    if isinstance(rankings, list):
        return rankings
    if "competitor_rankings" in payload:
        return [payload]
    return []


def _parent_id(parent: Any) -> str | None:
    if isinstance(parent, Mapping):
        return parent.get("id")
    if isinstance(parent, str):
        return parent
    return None


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
