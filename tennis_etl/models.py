"""Relational schema for Tennis Rankings Explorer."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy table mappings."""


class Category(Base):
    """Tour category such as ATP, WTA, or ITF."""

    __tablename__ = "categories"

    category_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)

    competitions: Mapped[list["Competition"]] = relationship(
        back_populates="category"
    )


class Competition(Base):
    """Competition returned by the SportRadar competitions feed."""

    __tablename__ = "competitions"

    competition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    competition_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("competitions.competition_id"),
        nullable=True,
    )
    type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.category_id"),
        nullable=False,
    )

    category: Mapped["Category"] = relationship(back_populates="competitions")
    parent: Mapped["Competition | None"] = relationship(
        remote_side=[competition_id]
    )


class Complex(Base):
    """Venue complex returned by the SportRadar complexes feed."""

    __tablename__ = "complexes"

    complex_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    complex_name: Mapped[str] = mapped_column(String(255), nullable=False)

    venues: Mapped[list["Venue"]] = relationship(back_populates="complex")


class Venue(Base):
    """Venue belonging to a complex."""

    __tablename__ = "venues"

    venue_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_name: Mapped[str] = mapped_column(String(255), nullable=False)
    city_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    complex_id: Mapped[str] = mapped_column(
        ForeignKey("complexes.complex_id"),
        nullable=False,
    )

    complex: Mapped["Complex"] = relationship(back_populates="venues")


class Competitor(Base):
    """Doubles competitor or team ranked by SportRadar."""

    __tablename__ = "competitors"

    competitor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    abbreviation: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ranking: Mapped["CompetitorRanking | None"] = relationship(
        back_populates="competitor"
    )


class CompetitorRanking(Base):
    """Current ranking row for a competitor."""

    __tablename__ = "competitor_rankings"
    __table_args__ = (
        UniqueConstraint("competitor_id", name="uq_competitor_rankings_competitor"),
    )

    rank_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    movement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competitions_played: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    competitor_id: Mapped[str] = mapped_column(
        ForeignKey("competitors.competitor_id"),
        nullable=False,
    )

    competitor: Mapped["Competitor"] = relationship(back_populates="ranking")
