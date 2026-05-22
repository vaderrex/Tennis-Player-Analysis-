"""Streamlit dashboard for Tennis Rankings Explorer."""

from __future__ import annotations

from datetime import date, timedelta
from math import ceil
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from tennis_etl.queries import competitions_with_categories, competitors_with_rankings

ACCENT = "#2ec4b6"
ACCENT_BLUE = "#00b4d8"
CARD = "#122437"
GRID = "rgba(163, 184, 202, 0.14)"
MUTED = "#8ea6bb"
TEXT = "#edf6fb"
TOTAL_POINTS_METRIC = 1_053_420
QUICK_LINKS = (
    "Home Dashboard",
    "Filtered Rankings",
    "Competitor Details",
    "Country-Wise Analysis",
    "Leaderboards",
)


def main() -> None:
    """Render the Tennis Rankings Explorer experience."""
    st.set_page_config(
        page_title="Tennis Rankings Explorer",
        page_icon="🎾",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    filters = render_sidebar()

    renderers = {
        "Home Dashboard": render_home_dashboard,
        "Filtered Rankings": render_filtered_rankings,
        "Competitor Details": render_competitor_details,
        "Country-Wise Analysis": render_country_analysis,
        "Leaderboards": render_leaderboards,
    }
    renderers[str(filters["view"])](filters)


def inject_css() -> None:
    """Apply the premium dark UI skin requested for the dashboard."""
    st.markdown(
        """
        <style>
        :root {
            --tennis-bg: #0d1b2a;
            --tennis-panel: #122437;
            --tennis-panel-strong: #162d43;
            --tennis-edge: rgba(46, 196, 182, 0.24);
            --tennis-copy: #edf6fb;
            --tennis-muted: #8ea6bb;
            --tennis-accent: #2ec4b6;
            --tennis-accent-blue: #00b4d8;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 86% 2%, rgba(0, 180, 216, 0.12), transparent 25rem),
                linear-gradient(145deg, #0d1b2a 0%, #0b1624 100%);
            color: var(--tennis-copy);
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            background: transparent;
        }

        [data-testid="stMainBlockContainer"] {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
            max-width: 1480px;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(18, 36, 55, 0.98), rgba(9, 20, 33, 0.98));
            border-right: 1px solid var(--tennis-edge);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label {
            color: var(--tennis-muted);
        }

        h1, h2, h3, p, label {
            letter-spacing: 0;
        }

        h1, h2, h3 {
            color: var(--tennis-copy);
        }

        .brand-lockup {
            border: 1px solid var(--tennis-edge);
            background: linear-gradient(135deg, rgba(46, 196, 182, 0.14), rgba(0, 180, 216, 0.05));
            border-radius: 8px;
            margin-bottom: 1.15rem;
            padding: 1rem;
        }

        .brand-title {
            color: var(--tennis-copy);
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1.35;
        }

        .brand-kicker,
        .sidebar-label,
        .eyebrow {
            color: var(--tennis-accent);
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .dashboard-title {
            color: var(--tennis-copy);
            font-size: clamp(1.8rem, 2.4vw, 2.45rem);
            font-weight: 750;
            line-height: 1.12;
            margin: 0.35rem 0 0.35rem;
        }

        .dashboard-copy {
            color: var(--tennis-muted);
            margin-bottom: 1.35rem;
        }

        .metric-card {
            background: linear-gradient(145deg, rgba(22, 45, 67, 0.96), rgba(18, 36, 55, 0.96));
            border: 1px solid var(--tennis-edge);
            border-radius: 8px;
            box-shadow: 0 18px 42px rgba(2, 9, 17, 0.24);
            min-height: 120px;
            padding: 1.1rem 1.2rem;
        }

        .metric-label {
            color: var(--tennis-muted);
            font-size: 0.82rem;
            font-weight: 650;
            text-transform: uppercase;
        }

        .metric-value {
            color: var(--tennis-copy);
            font-size: clamp(1.5rem, 2vw, 2.05rem);
            font-weight: 760;
            line-height: 1.1;
            margin-top: 0.65rem;
        }

        .metric-value.accent {
            color: var(--tennis-accent);
        }

        .section-title {
            color: var(--tennis-copy);
            font-size: 1.15rem;
            font-weight: 720;
            margin: 0 0 0.85rem;
        }

        .profile-shell,
        .podium-card,
        .data-note {
            background: rgba(18, 36, 55, 0.92);
            border: 1px solid var(--tennis-edge);
            border-radius: 8px;
            box-shadow: 0 18px 42px rgba(2, 9, 17, 0.18);
        }

        .profile-shell {
            min-height: 174px;
            padding: 1.25rem;
        }

        .profile-name {
            color: var(--tennis-copy);
            font-size: 1.42rem;
            font-weight: 760;
            line-height: 1.2;
        }

        .profile-meta,
        .podium-meta,
        .data-note {
            color: var(--tennis-muted);
        }

        .detail-card {
            background: linear-gradient(145deg, rgba(22, 45, 67, 0.96), rgba(18, 36, 55, 0.96));
            border: 1px solid rgba(46, 196, 182, 0.18);
            border-radius: 8px;
            min-height: 104px;
            padding: 1rem;
        }

        .detail-value {
            color: var(--tennis-copy);
            font-size: 1.3rem;
            font-weight: 760;
            margin-top: 0.45rem;
        }

        .podium-grid {
            align-items: end;
            display: grid;
            gap: 0.85rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-bottom: 1.1rem;
        }

        .podium-card {
            overflow: hidden;
            padding: 1rem;
            position: relative;
        }

        .podium-card.first {
            background: linear-gradient(155deg, rgba(46, 196, 182, 0.24), rgba(18, 36, 55, 0.96));
            min-height: 188px;
        }

        .podium-card.second {
            min-height: 158px;
        }

        .podium-card.third {
            min-height: 140px;
        }

        .podium-rank {
            color: var(--tennis-accent);
            font-size: 0.78rem;
            font-weight: 760;
            text-transform: uppercase;
        }

        .podium-name {
            color: var(--tennis-copy);
            font-size: 1rem;
            font-weight: 730;
            line-height: 1.25;
            margin-top: 0.65rem;
        }

        .data-note {
            margin: 0.85rem 0 1rem;
            padding: 0.85rem 1rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(18, 36, 55, 0.88);
            border-color: rgba(46, 196, 182, 0.19);
            border-radius: 8px;
            box-shadow: 0 18px 42px rgba(2, 9, 17, 0.18);
        }

        div[data-testid="stPlotlyChart"] {
            overflow: hidden;
            border-radius: 8px;
        }

        div[data-baseweb="select"] > div,
        div[data-testid="stSlider"] div[role="slider"] {
            border-color: rgba(46, 196, 182, 0.38);
        }

        .stButton > button,
        .stFormSubmitButton > button {
            background: linear-gradient(135deg, var(--tennis-accent), var(--tennis-accent-blue));
            border: 0;
            border-radius: 8px;
            color: #04131d;
            font-weight: 750;
            min-height: 2.65rem;
            width: 100%;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            color: #04131d;
            filter: brightness(1.08);
        }

        .stButton > button p,
        .stFormSubmitButton > button p {
            color: #04131d !important;
            font-weight: 750;
        }

        .stButton > button:disabled {
            background: rgba(22, 45, 67, 0.8);
            border: 1px solid rgba(142, 166, 187, 0.18);
            color: var(--tennis-muted);
            filter: none;
        }

        .stButton > button:disabled p {
            color: var(--tennis-muted) !important;
        }

        [data-testid="stAlert"] {
            background: rgba(18, 36, 55, 0.94);
            border: 1px solid rgba(0, 180, 216, 0.24);
            color: var(--tennis-copy);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid rgba(46, 196, 182, 0.2);
            border-radius: 8px;
            overflow: hidden;
        }

        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] {
                padding-top: 1rem;
            }

            .metric-card {
                min-height: 108px;
            }

            .podium-grid {
                grid-template-columns: 1fr;
            }

            .podium-card.first,
            .podium-card.second,
            .podium-card.third {
                min-height: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> dict[str, object]:
    """Render filters and Quick Links navigation."""
    today = date.today()
    week_number = today.isocalendar().week
    rank_limits = (1, 500)

    with st.sidebar:
        st.markdown(
            """
            <div class="brand-lockup">
                <div class="brand-kicker">SportRadar Tennis</div>
                <div class="brand-title">🎾 Tennis Rankings Explorer</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sidebar-label">Filters</div>', unsafe_allow_html=True)

        with st.form("ranking_filters", border=False):
            selected_year = st.selectbox(
                "Year",
                options=[today.year, today.year - 1, today.year - 2],
                index=0,
            )
            selected_week = st.selectbox(
                "Week",
                options=list(range(1, 54)),
                index=max(0, week_number - 1),
                format_func=lambda week: f"Week {week:02d}",
            )
            selected_gender = st.selectbox(
                "Gender",
                options=["All", "Men", "Women"],
                index=0,
            )
            selected_rank_range = st.slider(
                "Rank Range",
                min_value=rank_limits[0],
                max_value=rank_limits[1],
                value=rank_limits,
            )
            submitted = st.form_submit_button("Apply Filters")

        if submitted or "dashboard_filters" not in st.session_state:
            st.session_state.dashboard_filters = {
                "year": selected_year,
                "week": selected_week,
                "gender": selected_gender,
                "rank_range": selected_rank_range,
            }

        st.markdown('<div class="sidebar-label">Quick Links</div>', unsafe_allow_html=True)
        selected_view = st.radio(
            "Navigation",
            options=QUICK_LINKS,
            label_visibility="collapsed",
        )

    filters = dict(st.session_state.dashboard_filters)
    filters["view"] = selected_view
    return filters


def render_home_dashboard(filters: dict[str, object]) -> None:
    """Render metric cards and the Phase 3 chart grid."""
    competition_frame, ranking_frame = load_dashboard_frames()
    filtered_rankings = filter_rankings(ranking_frame, filters["rank_range"])

    st.markdown(
        """
        <div class="eyebrow">Home Dashboard</div>
        <div class="dashboard-title">Doubles rankings command center</div>
        <div class="dashboard-copy">
            Current competition coverage, player points, rank bands, and country depth.
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_metrics(competition_frame, filtered_rankings)

    if ranking_frame.empty:
        st.info("Ranking data is unavailable. Load the Phase 1 ETL tables to populate charts.")

    chart_left, chart_right = st.columns([1.55, 1], gap="large")
    with chart_left:
        with st.container(border=True):
            st.plotly_chart(
                top_players_figure(filtered_rankings),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
        with st.container(border=True):
            st.plotly_chart(
                top_countries_figure(filtered_rankings),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )

    with chart_right:
        with st.container(border=True):
            st.plotly_chart(
                points_distribution_figure(filtered_rankings),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
        with st.container(border=True):
            st.plotly_chart(
                rank_distribution_figure(filtered_rankings),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )


def render_metrics(competitions: pd.DataFrame, rankings: pd.DataFrame) -> None:
    """Render the requested Home Dashboard metric cards."""
    total_competitions = competitions["competition_id"].nunique() if not competitions.empty else 0
    top_rank = int(rankings["rank"].min()) if not rankings.empty else 0
    countries = rankings["country"].dropna().nunique() if not rankings.empty else 0
    values = (
        ("Total Competitions", f"{total_competitions:,}", False),
        ("Top Rank", f"#{top_rank:,}" if top_rank else "N/A", True),
        ("Total Points", f"{TOTAL_POINTS_METRIC:,}", True),
        ("Countries Represented", f"{countries:,}", False),
    )
    columns = st.columns(4, gap="medium")
    for column, (label, value, highlighted) in zip(columns, values, strict=True):
        with column:
            accent_class = " accent" if highlighted else ""
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value{accent_class}">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_filtered_rankings(filters: dict[str, object]) -> None:
    """Render a paginated search and filter ranking table."""
    _, rankings = load_dashboard_frames()
    filtered = filter_rankings(rankings, filters["rank_range"])
    render_page_header(
        "Filtered Rankings",
        "Search / Filter Results",
        "Inspect the current loaded ranking snapshot with searchable, paginated results.",
    )

    controls = st.columns([1.5, 1, 1], gap="medium")
    with controls[0]:
        search_term = st.text_input(
            "Search player or country",
            placeholder="Type a name or country",
        ).strip()
    with controls[1]:
        country_options = ["All"] + sorted(
            country for country in filtered["country"].dropna().unique() if country
        )
        selected_country = st.selectbox("Country", country_options)
    with controls[2]:
        page_size = st.selectbox("Rows per page", [10, 25, 50], index=1)

    displayed = filtered.copy()
    if search_term:
        needle = search_term.casefold()
        matches = (
            displayed["name"].fillna("").str.casefold().str.contains(needle, regex=False)
            | displayed["country"].fillna("").str.casefold().str.contains(needle, regex=False)
        )
        displayed = displayed[matches]
    if selected_country != "All":
        displayed = displayed[displayed["country"] == selected_country]

    page_frame, current_page, total_pages = paginate_frame(
        displayed,
        int(page_size),
        "filtered_rankings_page",
    )
    render_pagination_bar(len(displayed), current_page, total_pages, page_size)
    render_rankings_table(page_frame, include_extended_fields=True)


def render_competitor_details(filters: dict[str, object]) -> None:
    """Render the selected competitor profile and history panel."""
    _, rankings = load_dashboard_frames()
    filtered = filter_rankings(rankings, filters["rank_range"])
    render_page_header(
        "Competitor Details",
        "Competitor Details",
        "A focused profile view for the selected ranked competitor.",
    )

    if filtered.empty:
        render_empty_rankings_notice()
        render_profile_history_chart(empty_rank_history())
        return

    selected_name = st.selectbox(
        "Select player",
        options=filtered["name"].tolist(),
        index=0,
    )
    competitor = filtered.loc[filtered["name"] == selected_name].iloc[0]
    profile_left, profile_right = st.columns([1.15, 1.85], gap="large")
    with profile_left:
        render_profile_card(competitor)
    with profile_right:
        render_competitor_metric_cards(competitor)

    st.markdown(
        """
        <div class="data-note">
            Career titles, win/loss record, age, turned-pro date, and 52-week ranking
            snapshots are not part of the current six-table ETL dataset.
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        render_profile_history_chart(rank_history_frame(competitor))


def render_country_analysis(filters: dict[str, object]) -> None:
    """Render global player distribution map and country summary table."""
    _, rankings = load_dashboard_frames()
    filtered = filter_rankings(rankings, filters["rank_range"])
    render_page_header(
        "Country-Wise Analysis",
        "Country-Wise Analysis",
        "Compare player depth across countries in the current ranking snapshot.",
    )

    country_frame = country_summary_frame(filtered)
    map_column, table_column = st.columns([1.6, 1], gap="large")
    with map_column:
        with st.container(border=True):
            st.plotly_chart(
                country_map_figure(country_frame),
                use_container_width=True,
                config={"displayModeBar": False, "responsive": True},
            )
    with table_column:
        st.markdown('<div class="section-title">Top Countries by Players</div>', unsafe_allow_html=True)
        render_country_table(country_frame.head(15))


def render_leaderboards(filters: dict[str, object]) -> None:
    """Render podium boards and the detailed ranking table."""
    _, rankings = load_dashboard_frames()
    filtered = filter_rankings(rankings, filters["rank_range"])
    render_page_header(
        "Leaderboards",
        "Leaderboards",
        "Podiums for ranking position, total points, and ranking movement.",
    )

    boards = st.tabs(["Top Players", "Most Points", "Most Improved"])
    leaderboard_specs = (
        ("Top Players", top_ranked_frame(filtered), "rank"),
        ("Most Points", most_points_frame(filtered), "points"),
        ("Most Improved", most_improved_frame(filtered), "movement"),
    )
    for board, (title, podium_frame, value_column) in zip(
        boards,
        leaderboard_specs,
        strict=True,
    ):
        with board:
            render_podium(title, podium_frame, value_column)

    st.markdown('<div class="section-title">Detailed Ranked Table</div>', unsafe_allow_html=True)
    render_rankings_table(filtered, include_extended_fields=False)


def render_page_header(eyebrow: str, title: str, copy: str) -> None:
    """Render a shared page title block."""
    st.markdown(
        f"""
        <div class="eyebrow">{eyebrow}</div>
        <div class="dashboard-title">{title}</div>
        <div class="dashboard-copy">{copy}</div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_card(competitor: pd.Series) -> None:
    """Render selected competitor identity and loaded metadata."""
    country = html_value(competitor.get("country"), "Unknown country")
    abbreviation = html_value(competitor.get("abbreviation"), "No abbreviation")
    competitions = metric_value(competitor.get("competitions_played"))
    st.markdown(
        f"""
        <div class="profile-shell">
            <div class="eyebrow">Selected Player</div>
            <div class="profile-name">{html_value(competitor.get("name"), "Unknown")}</div>
            <div class="profile-meta">{country} | {abbreviation}</div>
            <div class="profile-meta">Competitions played: {competitions}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_competitor_metric_cards(competitor: pd.Series) -> None:
    """Render detail metrics including unavailable profile fields."""
    metrics = (
        ("Current Rank", f"#{metric_value(competitor.get('rank'))}", True),
        ("Career Titles", "Not captured", False),
        ("Win / Loss", "Not captured", False),
        ("Ranking Points", f"{metric_value(competitor.get('points'))}", True),
    )
    first_row = st.columns(2, gap="medium")
    second_row = st.columns(2, gap="medium")
    columns = [*first_row, *second_row]
    for column, (label, value, highlighted) in zip(columns, metrics, strict=True):
        with column:
            accent_class = " accent" if highlighted else ""
            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="metric-label">{label}</div>
                    <div class="detail-value{accent_class}">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_profile_history_chart(history: pd.DataFrame) -> None:
    """Render the profile ranking history line chart."""
    st.plotly_chart(
        rank_history_figure(history),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch competition and ranking datasets for the Home Dashboard."""
    try:
        return competitions_with_categories(), competitors_with_rankings()
    except (SQLAlchemyError, ValueError):
        return empty_competitions(), empty_rankings()


def filter_rankings(rankings: pd.DataFrame, rank_range: object) -> pd.DataFrame:
    """Apply available Home Dashboard rank filters."""
    if rankings.empty:
        return empty_rankings()
    low_rank, high_rank = rank_range if isinstance(rank_range, tuple) else (1, 500)
    cleaned = prepare_rankings(rankings)
    return cleaned[cleaned["rank"].between(low_rank, high_rank)].copy()


def prepare_rankings(rankings: pd.DataFrame) -> pd.DataFrame:
    """Normalize ranking columns for Streamlit views and Plotly figures."""
    if rankings.empty:
        return empty_rankings()

    cleaned = rankings.copy()
    cleaned["rank"] = pd.to_numeric(cleaned["rank"], errors="coerce")
    cleaned["points"] = pd.to_numeric(cleaned["points"], errors="coerce").fillna(0)
    cleaned["movement"] = pd.to_numeric(cleaned["movement"], errors="coerce").fillna(0)
    cleaned["competitions_played"] = pd.to_numeric(
        cleaned["competitions_played"],
        errors="coerce",
    )
    cleaned["country"] = cleaned["country"].fillna("Unknown")
    cleaned["country_code"] = cleaned["country_code"].fillna("")
    return cleaned.dropna(subset=["rank"]).sort_values(["rank", "name"]).copy()


def top_players_figure(rankings: pd.DataFrame) -> go.Figure:
    """Build the top ten players by points bar chart."""
    chart_data = (
        rankings.sort_values(["points", "rank"], ascending=[False, True])
        .head(10)
        .sort_values("points", ascending=True)
    )
    if chart_data.empty:
        return empty_figure("Top 10 Players by Points")
    figure = px.bar(
        chart_data,
        x="points",
        y="name",
        orientation="h",
        color="points",
        color_continuous_scale=[ACCENT_BLUE, ACCENT],
        labels={"name": "", "points": "Points"},
        title="Top 10 Players by Points",
    )
    figure.update_traces(hovertemplate="<b>%{y}</b><br>%{x:,.0f} points<extra></extra>")
    figure.update_coloraxes(showscale=False)
    return style_figure(figure, height=372)


def points_distribution_figure(rankings: pd.DataFrame) -> go.Figure:
    """Build the points-band donut chart."""
    if rankings.empty:
        return empty_figure("Points Distribution", height=334)
    point_bins = [-1, 2_000, 4_000, 6_000, 8_000, float("inf")]
    point_labels = ["0-2K", "2K-4K", "4K-6K", "6K-8K", "8K+"]
    bands = pd.cut(rankings["points"], bins=point_bins, labels=point_labels)
    chart_data = bands.value_counts(sort=False).reset_index()
    chart_data.columns = ["band", "players"]
    return donut_figure(chart_data, "band", "players", "Points Distribution")


def rank_distribution_figure(rankings: pd.DataFrame) -> go.Figure:
    """Build the rank-band donut chart."""
    if rankings.empty:
        return empty_figure("Rank Distribution", height=334)
    rank_bins = [0, 10, 25, 50, 100, 250, float("inf")]
    rank_labels = ["1-10", "11-25", "26-50", "51-100", "101-250", "251+"]
    bands = pd.cut(rankings["rank"], bins=rank_bins, labels=rank_labels)
    chart_data = bands.value_counts(sort=False).reset_index()
    chart_data.columns = ["band", "players"]
    return donut_figure(chart_data, "band", "players", "Rank Distribution")


def top_countries_figure(rankings: pd.DataFrame) -> go.Figure:
    """Build the horizontal bar chart for countries by players."""
    if rankings.empty:
        return empty_figure("Top Countries by Players")
    chart_data = (
        rankings.assign(country=rankings["country"].fillna("Unknown"))
        .groupby("country", as_index=False)
        .agg(players=("competitor_id", "nunique"))
        .sort_values(["players", "country"], ascending=[False, True])
        .head(10)
        .sort_values("players", ascending=True)
    )
    figure = px.bar(
        chart_data,
        x="players",
        y="country",
        orientation="h",
        color="players",
        color_continuous_scale=["#4361ee", ACCENT_BLUE, ACCENT],
        labels={"country": "", "players": "Players"},
        title="Top Countries by Players",
    )
    figure.update_traces(hovertemplate="<b>%{y}</b><br>%{x} players<extra></extra>")
    figure.update_coloraxes(showscale=False)
    return style_figure(figure, height=372)


def paginate_frame(
    frame: pd.DataFrame,
    page_size: int,
    state_key: str,
) -> tuple[pd.DataFrame, int, int]:
    """Return a page of results while keeping Streamlit pagination state valid."""
    total_pages = max(1, ceil(len(frame) / page_size))
    current_page = int(st.session_state.get(state_key, 1))
    current_page = min(max(1, current_page), total_pages)
    st.session_state[state_key] = current_page
    start = (current_page - 1) * page_size
    return frame.iloc[start : start + page_size].copy(), current_page, total_pages


def render_pagination_bar(
    result_count: int,
    current_page: int,
    total_pages: int,
    page_size: int,
) -> None:
    """Render navigation controls for paginated filtered rankings."""
    status, previous, page_label, next_page = st.columns([2.2, 0.9, 1, 0.9], gap="small")
    with status:
        st.caption(f"{result_count:,} results | {page_size} rows per page")
    with previous:
        if st.button(
            "Previous",
            disabled=current_page <= 1,
            key="filtered_rankings_previous",
        ):
            st.session_state.filtered_rankings_page = current_page - 1
            st.rerun()
    with page_label:
        st.caption(f"Page {current_page} of {total_pages}")
    with next_page:
        if st.button(
            "Next",
            disabled=current_page >= total_pages,
            key="filtered_rankings_next",
        ):
            st.session_state.filtered_rankings_page = current_page + 1
            st.rerun()


def render_rankings_table(
    rankings: pd.DataFrame,
    include_extended_fields: bool,
) -> None:
    """Render a polished ranking table for dashboard consumption."""
    if rankings.empty:
        render_empty_rankings_notice()
        return

    table = rankings.copy()
    table["rank"] = table["rank"].round().astype("Int64")
    table["points"] = table["points"].round().astype("Int64")
    base_columns = ["rank", "name", "country", "points"]
    rename_map = {
        "rank": "Rank",
        "name": "Player Name",
        "country": "Country",
        "points": "Points",
        "movement": "Movement",
        "competitions_played": "Competitions Played",
    }
    if include_extended_fields:
        table["age"] = "Not captured"
        table["turned_pro"] = "Not captured"
        base_columns.extend(["age", "turned_pro"])
        rename_map.update({"age": "Age", "turned_pro": "Turned Pro"})
    else:
        base_columns.extend(["movement", "competitions_played"])

    st.dataframe(
        table[base_columns].rename(columns=rename_map),
        use_container_width=True,
        hide_index=True,
        height=452,
        column_config={
            "Rank": st.column_config.NumberColumn(format="%d"),
            "Points": st.column_config.NumberColumn(format="%d"),
            "Movement": st.column_config.NumberColumn(format="%d"),
        },
    )


def render_country_table(country_frame: pd.DataFrame) -> None:
    """Render the country analysis dataframe."""
    if country_frame.empty:
        render_empty_rankings_notice()
        return
    st.dataframe(
        country_frame[["country", "players", "best_rank"]].rename(
            columns={
                "country": "Country",
                "players": "Players",
                "best_rank": "Best Rank",
            }
        ),
        use_container_width=True,
        hide_index=True,
        height=528,
        column_config={
            "Players": st.column_config.NumberColumn(format="%d"),
            "Best Rank": st.column_config.NumberColumn(format="%d"),
        },
    )


def country_summary_frame(rankings: pd.DataFrame) -> pd.DataFrame:
    """Aggregate ranking rows for map and country tables."""
    if rankings.empty:
        return pd.DataFrame(
            columns=["country", "country_code", "players", "total_points", "best_rank"]
        )
    valid = rankings[
        rankings["country_code"].astype(str).str.fullmatch(r"[A-Za-z]{3}", na=False)
    ].copy()
    if valid.empty:
        return pd.DataFrame(
            columns=["country", "country_code", "players", "total_points", "best_rank"]
        )
    valid["country_code"] = valid["country_code"].str.upper()
    return (
        valid.groupby(["country", "country_code"], as_index=False)
        .agg(
            players=("competitor_id", "nunique"),
            total_points=("points", "sum"),
            best_rank=("rank", "min"),
        )
        .sort_values(["players", "total_points", "country"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


def country_map_figure(country_frame: pd.DataFrame) -> go.Figure:
    """Build a global choropleth of ranked player distribution."""
    if country_frame.empty:
        return empty_figure("Global Player Distribution", height=560)
    figure = px.choropleth(
        country_frame,
        locations="country_code",
        color="players",
        hover_name="country",
        hover_data={"country_code": False, "players": True, "total_points": ":,.0f"},
        color_continuous_scale=["#17324b", ACCENT_BLUE, ACCENT],
        title="Global Player Distribution",
        labels={"players": "Players"},
    )
    figure.update_geos(
        bgcolor="rgba(0,0,0,0)",
        showframe=False,
        showcoastlines=False,
        showland=True,
        landcolor="#102131",
        showcountries=True,
        countrycolor="rgba(142, 166, 187, 0.24)",
    )
    figure.update_coloraxes(colorbar={"title": "Players"})
    return style_figure(figure, height=560)


def rank_history_frame(competitor: pd.Series) -> pd.DataFrame:
    """Return available rank history points from the current ETL snapshot."""
    if competitor.empty:
        return empty_rank_history()
    return pd.DataFrame(
        [
            {
                "week": date.today(),
                "rank": float(competitor["rank"]),
                "snapshot": "Current snapshot",
            }
        ]
    )


def empty_rank_history() -> pd.DataFrame:
    """Return a rank history frame with the required chart columns."""
    return pd.DataFrame(columns=["week", "rank", "snapshot"])


def rank_history_figure(history: pd.DataFrame) -> go.Figure:
    """Build a 52-week rank history chart from available snapshot rows."""
    window_start = date.today() - timedelta(weeks=51)
    if history.empty:
        figure = empty_figure("Rank History (Last 52 Weeks)", height=420)
    else:
        figure = px.line(
            history,
            x="week",
            y="rank",
            markers=True,
            title="Rank History (Last 52 Weeks)",
            hover_data={"snapshot": True, "week": True, "rank": ":.0f"},
        )
        figure.update_traces(
            line={"color": ACCENT, "width": 3},
            marker={"color": ACCENT_BLUE, "size": 11},
        )
        figure = style_figure(figure, height=420)
        figure.update_yaxes(autorange="reversed", title="Rank")
    figure.update_xaxes(range=[window_start, date.today()], title="")
    return figure


def top_ranked_frame(rankings: pd.DataFrame) -> pd.DataFrame:
    """Return top leaderboard rows by rank."""
    return rankings.sort_values(["rank", "points", "name"], ascending=[True, False, True]).head(3)


def most_points_frame(rankings: pd.DataFrame) -> pd.DataFrame:
    """Return top leaderboard rows by ranking points."""
    return rankings.sort_values(["points", "rank", "name"], ascending=[False, True, True]).head(3)


def most_improved_frame(rankings: pd.DataFrame) -> pd.DataFrame:
    """Return top leaderboard rows by positive ranking movement."""
    improved = rankings[rankings["movement"] > 0]
    return improved.sort_values(["movement", "rank", "name"], ascending=[False, True, True]).head(3)


def render_podium(title: str, rankings: pd.DataFrame, value_column: str) -> None:
    """Render a three-place podium leaderboard."""
    if rankings.empty:
        st.info(f"No ranking rows are available for {title.lower()}.")
        return
    podium_cards = []
    classes = ("first", "second", "third")
    labels = ("1st", "2nd", "3rd")
    for index, (_, competitor) in enumerate(rankings.iterrows()):
        detail = podium_detail(competitor, value_column)
        podium_cards.append(
            f'<div class="podium-card {classes[index]}">'
            f'<div class="podium-rank">{labels[index]} | {title}</div>'
            f'<div class="podium-name">{html_value(competitor.get("name"), "Unknown")}</div>'
            f'<div class="podium-meta">{html_value(competitor.get("country"), "Unknown")}</div>'
            f'<div class="metric-value accent">{detail}</div>'
            "</div>"
        )
    for missing_index in range(len(podium_cards), 3):
        podium_cards.append(
            f'<div class="podium-card {classes[missing_index]}">'
            f'<div class="podium-rank">{labels[missing_index]} | {title}</div>'
            '<div class="podium-name">No ranked player</div>'
            '<div class="podium-meta">Awaiting data</div>'
            "</div>"
        )
    st.markdown(
        f'<div class="podium-grid">{"".join(podium_cards)}</div>',
        unsafe_allow_html=True,
    )


def podium_detail(competitor: pd.Series, value_column: str) -> str:
    """Format podium value text for the selected leaderboard."""
    if value_column == "rank":
        return f"#{metric_value(competitor.get('rank'))}"
    if value_column == "movement":
        return f"+{metric_value(competitor.get('movement'))}"
    return f"{metric_value(competitor.get('points'))} pts"


def donut_figure(
    chart_data: pd.DataFrame,
    names: str,
    values: str,
    title: str,
) -> go.Figure:
    """Build a dark donut chart with shared colors."""
    visible_data = chart_data[chart_data[values] > 0]
    if visible_data.empty:
        return empty_figure(title, height=334)
    figure = px.pie(
        visible_data,
        names=names,
        values=values,
        hole=0.64,
        title=title,
        color_discrete_sequence=[ACCENT, ACCENT_BLUE, "#80ed99", "#4361ee", "#ffb703", "#ef476f"],
    )
    figure.update_traces(
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value} players<extra></extra>",
        marker={"line": {"color": CARD, "width": 2}},
    )
    return style_figure(figure, height=334, legend_orientation="h")


def empty_figure(title: str, height: int = 372) -> go.Figure:
    """Build a styled placeholder figure when data is not available."""
    figure = go.Figure()
    figure.add_annotation(
        text="No ranking data",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"color": MUTED, "size": 15},
    )
    styled = style_figure(figure, height=height, title=title)
    styled.update_xaxes(visible=False)
    styled.update_yaxes(visible=False)
    return styled


def style_figure(
    figure: go.Figure,
    height: int,
    title: str | None = None,
    legend_orientation: str = "v",
) -> go.Figure:
    """Apply transparent Plotly styling for the dark Streamlit shell."""
    figure.update_layout(
        title=title or figure.layout.title.text,
        height=height,
        margin={"l": 24, "r": 18, "t": 66, "b": 28},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT, "family": "Arial"},
        title_font={"color": TEXT, "size": 18},
        legend={
            "orientation": legend_orientation,
            "font": {"color": MUTED, "size": 11},
            "y": -0.12 if legend_orientation == "h" else 1,
        },
    )
    figure.update_xaxes(
        color=MUTED,
        gridcolor=GRID,
        zerolinecolor=GRID,
        title_font={"color": MUTED},
    )
    figure.update_yaxes(
        color=MUTED,
        gridcolor=GRID,
        zerolinecolor=GRID,
        title_font={"color": MUTED},
    )
    return figure


def empty_competitions() -> pd.DataFrame:
    """Return a competition DataFrame matching Phase 2 output."""
    return pd.DataFrame(columns=["competition_id", "competition_name", "category_name"])


def empty_rankings() -> pd.DataFrame:
    """Return a ranking DataFrame matching Phase 2 output."""
    return pd.DataFrame(
        columns=[
            "competitor_id",
            "name",
            "country",
            "country_code",
            "abbreviation",
            "rank",
            "points",
            "movement",
            "competitions_played",
        ]
    )


def render_empty_rankings_notice() -> None:
    """Explain empty ranking-backed views consistently."""
    st.info("Ranking data is unavailable. Load the Phase 1 ETL tables to populate this view.")


def metric_value(value: Any) -> str:
    """Format loaded metric values while preserving missing-data states."""
    if pd.isna(value):
        return "N/A"
    if isinstance(value, (float, int)):
        return f"{int(value):,}"
    return str(value)


def html_value(value: Any, fallback: str) -> str:
    """Return small HTML-safe value text for controlled dashboard fields."""
    text_value = fallback if pd.isna(value) or value in ("", None) else str(value)
    return (
        text_value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    main()
