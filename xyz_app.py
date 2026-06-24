from __future__ import annotations
import os
import html
import textwrap
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from dotenv import load_dotenv

# --- DATABASE CONNECTION & SAFE FALLBACKS ---
try:
    from tennis_etl.queries import (
        competitions_with_categories, 
        competitors_with_rankings
    )
    get_competitions = st.cache_data(competitions_with_categories)
    get_competitors = st.cache_data(competitors_with_rankings)
except ImportError:
    def get_competitions(): 
        return pd.DataFrame(columns=["competition_id", "gender", "category", "name"])
    def get_competitors(): 
        return pd.DataFrame(columns=["competitor_id", "rank", "name", "country", "points", "movement", "competitions_played", "gender"])

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# --- GLASSMORPHISM COLOR PALETTE ---
HEX_TEXT_MAIN = "#2B3674"   
HEX_TEXT_MUTED = "#707EAE"  
COLOR_PRIMARY = "#8A2BE2"   

def init_interface():
    """Inject Deep Glassmorphism UI CSS overrides matching application theme."""
    st.set_page_config(
        page_title="Tennis Core | Analytics Console",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Poppins', sans-serif !important;
            letter-spacing: -0.01em;
        }
        /* ── RESTORE MATERIAL ICONS BROKEN BY GLOBAL FONT OVERRIDE ── */
        span[data-testid="stIconMaterial"],
        i[data-testid="stIconMaterial"],
        .st-emotion-cache-pisvoc {
            font-family: 'Material Symbols Rounded' !important;
            font-weight: normal !important;
            font-style: normal !important;
            font-size: 24px !important;
            line-height: 1 !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            display: inline-block !important;
            white-space: nowrap !important;
            word-wrap: normal !important;
        }

        /* ── MESH GRADIENT BACKGROUND ── */
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(ellipse at 20% 20%, rgba(181,160,255,.40) 0%, transparent 50%),
                radial-gradient(ellipse at 90% 10%, rgba(155,240,255,.35) 0%, transparent 50%),
                radial-gradient(ellipse at 75% 85%, rgba(255,180,230,.30) 0%, transparent 50%),
                radial-gradient(ellipse at 5% 85%, rgba(190,200,255,.25) 0%, transparent 50%),
                #F0EEF8 !important;
            background-attachment: fixed !important;
            min-height: 100vh !important;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"] {
            background: transparent !important;
        }
        [data-testid="stMainBlockContainer"] {
            padding: 2rem 2.5rem !important;
            max-width: 1680px !important;
        }

        /* ── SIDEBAR ── */
        section[data-testid="stSidebar"] {
            margin: 16px 0px 16px 16px !important;
            border-radius: 24px !important;
            height: calc(100vh - 32px) !important;
            background: linear-gradient(160deg, rgba(255, 255, 255, 0.95) 0%, rgba(235, 230, 255, 0.92) 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.9) !important;
            box-shadow: 0 8px 32px rgba(138, 43, 226, 0.08) !important;
            backdrop-filter: blur(40px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(40px) saturate(180%) !important;
            overflow: hidden !important;
        }
        [data-testid="stSidebarContent"] {
            padding: 1.5rem 1.2rem !important;
            background: transparent !important;
        }

        /* ── SIDEBAR BRAND ── */
        .sidebar-brand {
            display: flex; align-items: center; gap: 5x;
            padding: 0.2rem 0 1rem 0;
            border-bottom: 1px solid rgba(138,43,226,0.06);
            margin-bottom: 0.8rem;
        }
        .brand-icon {
            width: 42px; height: 42px; border-radius: 50%;
            background: linear-gradient(135deg, #7C3AED, #A855F7);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.2);
        }
        .brand-title { font-size: 2rem; font-weight: 800; color: #2B3674 !important; line-height: 1.1; }
        .brand-sub   { font-size: 1rem; color: #8A7FBE !important; font-weight: 500; }
        .brand-collapse-btn {
            margin-left: auto; width: 28px; height: 28px;
            border-radius: 50%; background: rgba(255,255,255,0.8);
            border: 1px solid rgba(225,220,255,0.8);
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; color: #8A7FBE; font-size: 0.7rem;
            box-shadow: 0 2px 6px rgba(100, 80, 200, 0.08);
            transition: all 0.2s ease;
        }
        .brand-collapse-btn:hover {
            background: #fff;
            color: #7C3AED;
            transform: scale(1.05);
        }

        /* ── SIDEBAR RESET BUTTON ── */
       

        /* ── SECTION HEADINGS ── */
        .sidebar-section-heading {
            display: flex; align-items: center; gap: 8px;
            font-size: 0.72rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 1.5px;
            color: #8A7FBE;
            margin: 1.4rem 0 0.8rem 0;
        }
        .sidebar-section-heading svg { flex-shrink: 0; }
        .sidebar-divider { height: 1px; background: linear-gradient(90deg, rgba(138,43,226,0.1), transparent); margin: 0.7rem 0; }

        /* NAV and SEGMENTED overrides are defined below in the main override block */


        /* ── FILTER LABEL ── */
        .filter-label {
            font-size: 0.82rem; font-weight: 600;
            color: #2B2F6E;
            margin: 0.9rem 0 0.35rem 0;
            display: flex; align-items: center; gap: 6px;
        }
        .filter-label .info-dot {
            display: inline-flex; align-items: center; justify-content: center;
            width: 15px; height: 15px; border-radius: 50%;
            border: 1px solid rgba(138, 43, 226, 0.25);
            color: #8A2BE2; font-size: 0.52rem; font-weight: 700;
            background: rgba(138, 43, 226, 0.05);
            cursor: help;
        }

        /* ══════════════════════════════════════════════
           SIDEBAR BUTTON BASE: override ALL to light/transparent
           ══════════════════════════════════════════════ */
        [data-testid="stSidebar"] button,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
            background: transparent !important;
            color: #4A4875 !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 16px !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            width: 100% !important;
            transition: background 0.18s ease, color 0.18s ease !important;
        }

        /* ── RESET BUTTON  ── */


        /* ── NAV: ACTIVE = light purple pill, text = purple ──
           Selector anchored to stSidebar so it reliably matches regardless
           of the broken div-wrapper nesting pattern. The [id^="nav_"] 
           attribute targets only nav buttons by their key prefix.        */
        [data-testid="stSidebar"] button[kind="primary"],
        [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
            background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(225,215,255,0.88) 100%) !important;
            color: #6B21D9 !important;
            border: none !important;
            border-radius: 22px !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            padding: 0.9rem 1.2rem !important;
            justify-content: flex-start !important;
            gap: 10px !important;
            box-shadow: 0 8px 24px rgba(124, 58, 237, 0.18), inset 0 1px 0 rgba(255,255,255,0.9) !important;
        }
        /* NAV: INACTIVE = transparent, muted text */
        [data-testid="stSidebar"] button[kind="secondary"],
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
            background: rgba(255,255,255,.18) !important;
            backdrop-filter: blur(12px) !important;
            color: #4A4875 !important;
            border: 1px solid rgba(255,255,255,0.35) !important;
            border-radius: 20px !important;
            font-weight: 500 !important;
            font-size: 0.875rem !important;
            padding: 0.85rem 1.1rem !important;
            transition: all .25s ease;
            justify-content: flex-start !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:hover,
        [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
            background: rgba(255,255,255,0.55) !important;
            transform: translateX(6px);
            box-shadow: 0 6px 16px rgba(124,58,237,0.10);
            color: #2B2F6E !important;
        }


        /* ── SEGMENTED CONTROL wrapper ── */
        .segmented-control-container {
            background: rgba(220, 212, 255, 0.35) !important;
            border-radius: 16px !important;
            padding: 4px !important;
            border: 1px solid rgba(138, 43, 226, 0.10) !important;
            margin-bottom: 0.9rem !important;
        }
        /* Kill glass card from sidebar column wrappers — applies to both
           the segmented-control columns AND any other st.columns() inside
           the sidebar so the global column-glass rule is fully suppressed.  */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div:first-child,
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
            background: transparent !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            transform: none !important;
            border-radius: 0 !important;
        }
        /* ACTIVE toggle = purple gradient.
           Use [data-testid="stSidebar"] prefix + .segmented-control-container
           for higher specificity so these rules beat the sidebar-wide rules above. */
        [data-testid="stSidebar"] .segmented-control-container [data-testid="stBaseButton-primary"],
        [data-testid="stSidebar"] .segmented-control-container button[kind="primary"] {
            background: linear-gradient(135deg, #8B2EE0 0%, #7540EC 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 6px !important;
            justify-content: center !important;
            box-shadow: 0 3px 10px rgba(124, 58, 237, 0.30) !important;
            transform: none !important;
        }
        /* INACTIVE toggle = transparent text */
        [data-testid="stSidebar"] .segmented-control-container [data-testid="stBaseButton-secondary"],
        [data-testid="stSidebar"] .segmented-control-container button[kind="secondary"] {
            background: transparent !important;
            color: #7A72A8 !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 500 !important;
            font-size: 0.8rem !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 6px !important;
            justify-content: center !important;
            box-shadow: none !important;
        }
        [data-testid="stSidebar"] .segmented-control-container [data-testid="stBaseButton-secondary"]:hover,
        [data-testid="stSidebar"] .segmented-control-container button[kind="secondary"]:hover {
            background: rgba(255,255,255,0.55) !important;
            color: #2B2F6E !important;
            transform: none !important;
        }

        /* ── SELECTBOX INSIDE SIDEBAR ── */
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            background: rgba(255, 255, 255, 0.72) !important;
            border: 1px solid rgba(138, 43, 226, 0.13) !important;
            border-radius: 12px !important;
            color: #2B2F6E !important;
            font-size: 0.84rem !important;
            box-shadow: 0 2px 8px rgba(100, 80, 200, 0.04) !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
            border-color: rgba(124, 58, 237, 0.30) !important;
            background: rgba(255, 255, 255, 0.90) !important;
        }
        [data-testid="stSidebar"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] div[data-baseweb="select"] p {
            color: #2B2F6E !important;
        }
        [data-testid="stSidebar"] .stSelectbox label { display: none !important; }

        /* ── MISC ── */
        [data-testid="stSidebar"] .stRadio { display: none !important; }
        .sidebar-brand { padding: 0; margin: 0; }
        .brand-text { font-size: 1.75rem; font-weight: 800; color: #2B3674 !important; }
        .sidebar-heading { font-weight: 700 !important; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 1.5px; color: #A3AED0 !important; margin-bottom: 0.8rem; margin-top: 0.5rem; }

        /* ── WIDGET ENHANCEMENTS ── */
        div[data-testid="stTextInput"] input {
            background-color: rgba(255, 255, 255, 0.95) !important;
            border: 1px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 14px !important;
            color: #2B3674 !important;
            backdrop-filter: blur(10px) !important;
        }
        div[data-testid="stTextInput"] input::placeholder {
            color: #707EAE !important;
            opacity: 0.7 !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.55) !important;
            border: 1px solid rgba(255, 255, 255, 0.7) !important;
            border-radius: 14px !important;
            color: #2B3674 !important;
            backdrop-filter: blur(10px) !important;
        }
        div[data-baseweb="popover"] {
            background-color: rgba(255,255,255,0.96) !important;
            backdrop-filter: blur(20px) !important;
            border-radius: 14px !important;
            border: 1px solid rgba(255, 255, 255, 0.6) !important;
            box-shadow: 0 10px 30px rgba(150, 120, 200, 0.15) !important;
        }
        div[role="option"] { color: #2B3674 !important; font-family: 'Poppins', sans-serif !important; font-size: 0.9rem !important; padding: 8px 16px !important; }
        div[role="option"]:hover, div[role="option"][aria-selected="true"] { background-color: rgba(138,43,226,0.12) !important; color: #8A2BE2 !important; }

        /* ── SIDEBAR SELECTS & RADIO ── */
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] label { color: #48558f !important; font-weight: 600 !important; font-size: 0.8rem !important; margin-bottom: 0.3rem !important; }
        
        /* Main selectbox styling */
        .stSelectbox label {
            color: #2B3674 !important;
            font-weight: 700 !important;
            font-size: 0.9rem !important;
            margin-bottom: 0.5rem !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label p { font-weight: 500 !important; font-size: 0.88rem !important; color: #5a6a9c !important; }
        [data-testid="stSidebar"] div[role="radiogroup"] label[data-selected="true"] {
            background: linear-gradient(90deg, rgba(234,128,252,0.20), rgba(138,43,226,0.10)) !important;
            border-left: 3px solid #8A2BE2 !important;
            border-radius: 4px 12px 12px 4px !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label[data-selected="true"] p { color: #8A2BE2 !important; font-weight: 600 !important; }

        /* ══════════════════════════════════════════════════════════
           GLASS CARD — Both st.container(border=True) wrappers
           AND custom .glass-chart-card HTML div elements
           ══════════════════════════════════════════════════════════ */

        /* Reliable custom glass card class used in HTML markdown */
        .glass-chart-card {
            background: rgba(255, 255, 255, 0.52) !important;
            backdrop-filter: blur(20px) saturate(160%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
            border: 1px solid rgba(255, 255, 255, 0.82) !important;
            border-radius: 24px !important;
            box-shadow:
                0 4px 20px rgba(31, 38, 135, 0.08),
                0 1px 3px rgba(31, 38, 135, 0.04),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
            padding: 1.5rem !important;
            margin-bottom: 1rem !important;
            transition: transform 0.25s ease, box-shadow 0.25s ease !important;
            position: relative !important;
        }
        .glass-chart-card:hover {
            transform: translateY(-3px) !important;
            box-shadow:
                0 12px 32px rgba(31, 38, 135, 0.12),
                0 4px 8px rgba(31, 38, 135, 0.05),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
        }

        .glass-chart-card-Custom{
            background: rgba(255, 255, 255, 0.98) !important;
            backdrop-filter: blur(20px) saturate(160%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
            border: 1px solid rgba(255, 255, 255, 0.82) !important;
            border-radius: 24px !important;
            box-shadow:
                0 4px 20px rgba(31, 38, 135, 0.08),
                0 1px 3px rgba(31, 38, 135, 0.04),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
            padding: 1.5rem !important;
            margin-bottom: 1rem !important;
            transition: transform 0.25s ease, box-shadow 0.25s ease !important;
            position: relative !important;
            }
            .glass-chart-card-Custom:hover{
                transform: translateY(-3px) !important;
                box-shadow:
                0 12px 32px rgba(31, 38, 135, 0.12),
                0 4px 8px rgba(31, 38, 135, 0.05),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
            }

        /* COLUMN-LEVEL GLASS: apply to each column's content wrapper div
           so chart + title appear as one glass panel (Streamlit 1.40+) */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div:first-child {
            background: rgba(255, 255, 255, 0.50) !important;
            backdrop-filter: blur(24px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(24px) saturate(150%) !important;
            border: 1px solid rgba(255, 255, 255, 0.85) !important;
            border-radius: 24px !important;
            box-shadow:
                0 4px 24px rgba(31, 38, 135, 0.08),
                0 1px 4px rgba(31, 38, 135, 0.04),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
            padding: 1.5rem !important;
            margin-bottom: 0 !important;
            transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div:first-child:hover {
            transform: translateY(-3px) !important;
            box-shadow:
                0 14px 36px rgba(31, 38, 135, 0.12),
                0 4px 8px rgba(31, 38, 135, 0.05),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
        }
        /* Columns in the sidebar should NOT get glass styling — same rule
           as above, kept here for cascade specificity against the
           [data-testid="stHorizontalBlock"] column-glass rule immediately above. */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div:first-child,
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
            background: transparent !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            transform: none !important;
            border-radius: 0 !important;
        }

        /* Also style stVerticalBlockBorderWrapper for completeness */
        div[data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, 0.52) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.82) !important;
            border-radius: 24px !important;
            box-shadow:
                0 4px 20px rgba(31, 38, 135, 0.08),
                inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
            padding: 1.5rem !important;
            margin-bottom: 1rem !important;
            transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 14px 36px rgba(31, 38, 135, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
        }

        /* Remove inner stVerticalBlock default white bg */
        div[data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* Dark glass variant for map panels */
        .glass-chart-card.dark-glass,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.dark-glass-trigger) {
            background: rgba(15, 23, 42, 0.50) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            box-shadow: 0 12px 48px rgba(0, 0, 0, 0.22) !important;
        }
        .dark-glass-trigger { display: none !important; }

        /* Ensure column containers have no extra spacing that breaks card look */
        [data-testid="stColumn"] > div > .glass-chart-card {
            height: 100% !important;
        }

        /* ── GLASS HEADER TITLES ── */
        .glass-header {
            color: #2B3674 !important;
            font-size: 1.5rem !important;
            margin: 0 0 0.75rem 0 !important;
            padding: 1rem !important;
            letter-spacing: -0.02em !important;
            text-shadow: none !important;
        }
        
        /* Ensure all headings in glass cards are dark blue */
        .glass-chart-card h3,
        .glass-chart-card h4,
        [data-testid="stVerticalBlockBorderWrapper"] h3,
        [data-testid="stVerticalBlockBorderWrapper"] h4 {
            color: #2B3674 !important;
            font-weight: 700 !important;
            margin-bottom: 0.75rem !important;
        }
        
        /* Style for any markdown text inside containers */
        .glass-chart-card,
        [data-testid="stVerticalBlockBorderWrapper"] {
            position: relative;
        }

        /* ── KPI GLASS CARDS ── */
        .glass-card {
            background: rgba(255,255,255,0.55);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255,255,255,0.80);
            border-radius: 22px;
            box-shadow: 0 6px 28px rgba(31,38,135,0.07), inset 0 1px 0 rgba(255,255,255,0.9);
            padding: 1.25rem 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }
        .glass-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 14px 38px rgba(31,38,135,0.11), inset 0 1px 0 rgba(255,255,255,0.9);
        }

        /* ── LEADERBOARD / PODIUM CARDS ── */
        .leaderboard-container { display: flex; gap: 1.5rem; align-items: flex-end; justify-content: center; margin-bottom: 2rem; padding-top: 1rem; }
        .podium-card { flex: 1; max-width: 340px; text-align: center; border-radius: 20px; padding: 2rem 1.5rem 1.5rem 1.5rem; border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 8px 32px rgba(31,38,135,0.04); position: relative; }
        .podium-1 { background: rgba(255,215,0,0.15) !important; border: 2px solid rgba(255,215,0,0.4) !important; box-shadow: 0 10px 30px rgba(255,215,0,0.15) !important; height: 310px; backdrop-filter: blur(20px) !important; }
        .podium-2 { background: rgba(192,192,192,0.15) !important; border: 2px solid rgba(192,192,192,0.4) !important; box-shadow: 0 10px 30px rgba(192,192,192,0.1) !important; height: 290px; backdrop-filter: blur(20px) !important; }
        .podium-3 { background: rgba(205,127,50,0.15) !important; border: 2px solid rgba(205,127,50,0.4) !important; box-shadow: 0 10px 30px rgba(205,127,50,0.1) !important; height: 270px; backdrop-filter: blur(20px) !important; }
        .badge-medal { width: 44px; height: 44px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.2rem; color: white; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
        .medal-1 { background-color: #FAC822; }
        .medal-2 { background-color: #A4B0BE; }
        .medal-3 { background-color: #ECCC68; }
        .tour-indicator { display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; background: rgba(43,54,116,0.08); color: #2B3674; margin-top: 0.5rem; }

        /* ── TABS ── */
        button[data-baseweb="tab"] { font-family: 'Poppins', sans-serif !important; font-weight: 600 !important; }
        

        /* ── BUTTON RESET FILTERS (already defined above for sidebar) ── */




        [data-baseweb="select"] input,
        [data-baseweb="popover"] input {
            color: #2B3674 !important;
            -webkit-text-fill-color: #2B3674 !important;
            caret-color: #2B3674 !important;
        }




        
        </style>

        <script>
        /* Post-render glass reinforcement: runs once after Streamlit mounts components */
        (function applyGlass() {
            var glassStyle = [
                'background: rgba(255,255,255,0.50)',
                'backdrop-filter: blur(24px) saturate(150%)',
                '-webkit-backdrop-filter: blur(24px) saturate(150%)',
                'border: 1px solid rgba(255,255,255,0.85)',
                'border-radius: 24px',
                'box-shadow: 0 4px 24px rgba(31,38,135,0.08), inset 0 1px 0 rgba(255,255,255,0.95)',
                'padding: 1.5rem',
                'transition: transform 0.25s ease, box-shadow 0.25s ease'
            ].join(';');
            function style() {
                /* Style stVerticalBlockBorderWrapper (border=True containers) */
                document.querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]').forEach(function(el) {
                    el.style.cssText += glassStyle;
                });
                /* Style stColumn > div:first-child (column panels containing charts) */
                var blocks = document.querySelectorAll('[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div:first-child');
                blocks.forEach(function(el) {
                    /* Skip sidebar columns */
                    if (el.closest('[data-testid="stSidebar"]')) return;
                    el.style.cssText += glassStyle;
                });
            }
            /* Run immediately and after a short delay to catch lazy-rendered charts */
            style();
            setTimeout(style, 500);
            setTimeout(style, 1500);
            setTimeout(style, 3000);
            /* MutationObserver to catch dynamically added containers */
            var observer = new MutationObserver(function(mutations) {
                var hasNew = mutations.some(function(m) {
                    return m.addedNodes.length > 0;
                });
                if (hasNew) style();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        </script>
    """, unsafe_allow_html=True)

def style_canvas_chart(fig: go.Figure, height: int = 350) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        margin=dict(l=135, r=20, t=25, b=45),
        font=dict(color=HEX_TEXT_MAIN, family="Poppins, sans-serif", size=11),
        legend=dict(
            font=dict(color=HEX_TEXT_MAIN, size=11),
            title_font=dict(color=HEX_TEXT_MAIN, size=11),
            bgcolor="rgba(255,255,255,0)",
        ),
        coloraxis_colorbar=dict(
            title_font=dict(color=HEX_TEXT_MAIN, size=11),
            tickfont=dict(color=HEX_TEXT_MAIN, size=10),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        gridcolor="rgba(43, 54, 116, 0.08)",
        tickfont=dict(color=HEX_TEXT_MAIN, size=10),
        title_font=dict(color=HEX_TEXT_MAIN, size=11)
    )
    fig.update_yaxes(
        showgrid=False,
        gridcolor="rgba(43, 54, 116, 0.08)",
        tickfont=dict(color=HEX_TEXT_MAIN, size=11),
        title_font=dict(color=HEX_TEXT_MAIN, size=11)
    )
    return fig

def clean_gender_value(val: any) -> str:
    """Accurately map data values without substring collision errors."""
    if pd.isna(val):
        return "W"
    text = str(val).strip().upper()
    if "WOMEN" in text or text == "W" or "WTA" in text:
        return "W"
    return "M"

def country_code_to_flag(code: str) -> str:
    """Map ISO-3166-1 alpha-3 code to dynamic Unicode country flag emoji."""
    if not code:
        return "🏳️"
    code = str(code).strip().upper()
    iso3_to_iso2 = {
        "ARE": "AE", "ARG": "AR", "ATG": "AG", "AUS": "AU", "AUT": "AT", "BDI": "BI", "BEL": "BE",
        "BGR": "BG", "BHR": "BH", "BIH": "BA", "BOL": "BO", "BRA": "BR", "CAN": "CA", "CHE": "CH",
        "CHL": "CL", "CHN": "CN", "CIV": "CI", "COL": "CO", "CYP": "CY", "CZE": "CZ", "DEU": "DE",
        "DNK": "DK", "DOM": "DO", "ECU": "EC", "EGY": "EG", "ENG": "GB", "ESP": "ES", "EST": "EE",
        "FIN": "FI", "FRA": "FR", "GBR": "GB", "GEO": "GE", "GHA": "GH", "GRC": "GR", "HKG": "HK",
        "HRV": "HR", "HUN": "HU", "IDN": "ID", "IND": "IN", "IRL": "IE", "ISR": "IL", "ITA": "IT",
        "JPN": "JP", "KAZ": "KZ", "KEN": "KE", "KOR": "KR", "LBN": "LB", "LTU": "LT", "LUX": "LU",
        "LVA": "LV", "MAR": "MA", "MCO": "MC", "MDA": "MD", "MEX": "MX", "MKD": "MK", "MNP": "MP",
        "NCL": "NC", "NLD": "NL", "NOR": "NO", "NZL": "NZ", "PAK": "PK", "PER": "PE", "PHL": "PH",
        "POL": "PL", "PRT": "PT", "PRY": "PY", "QAT": "QA", "ROU": "RO", "RUS": "RU", "RWA": "RW",
        "SAU": "SA", "SCO": "GB", "SGP": "SG", "SLV": "SV", "SMR": "SM", "SRB": "RS", "SVK": "SK",
        "SVN": "SI", "SWE": "SE", "THA": "TH", "TPE": "TW", "TUN": "TN", "TUR": "TR", "UKR": "UA",
        "URY": "UY", "USA": "US", "UZB": "UZ", "VEN": "VE", "VNM": "VN", "ZAF": "ZA", "ZWE": "ZW"
    }
    iso2 = iso3_to_iso2.get(code)
    if not iso2:
        if len(code) == 2:
            iso2 = code
        else:
            return "🏳️"
    return "".join(chr(127397 + ord(c)) for c in iso2)

# --- ROUTING VIEW SEGMENT FUNCTIONS ---

def render_dashboard(df_comps: pd.DataFrame, df_ranks: pd.DataFrame):
    if df_ranks.empty:
        st.info("No competitor records match the selected sidebar filters.")
        return

    col1, col2 = st.columns([2, 2], gap="small")
    with col1:
        st.markdown("<h3 class='glass-header'>Top 10 Standings</h3>", unsafe_allow_html=True)
        top10 = df_ranks.nlargest(10, 'points').sort_values('points', ascending=True)
        fig1 = px.bar(top10, x='points', y='name', orientation='h', color='points', color_continuous_scale=["#E9D5FF", "#A855F7", "#6B21A8"])
        fig1.update_coloraxes(showscale=False)
        fig1.update_traces(width=0.4, marker_cornerradius=8, hovertemplate="<b>%{y}</b><br>Points: %{x:,}<extra></extra>", marker_line_width=0)
        fig1.update_xaxes(title_text="Points")
        fig1.update_yaxes(title_text="Name")
        st.plotly_chart(style_canvas_chart(fig1, height=340), use_container_width=True, config={"displayModeBar": False})

    with col2:
        st.markdown("<h3 class='glass-header'>Top Regions by Player Volume</h3>", unsafe_allow_html=True)
        if 'country' in df_ranks.columns:
            top_countries = df_ranks['country'].value_counts().nlargest(10).reset_index()
            top_countries.columns = ['country', 'count']
            top_countries = top_countries.sort_values('count', ascending=True)
        fig2 = px.bar(top_countries, x='count', y='country', orientation='h', color='count', color_continuous_scale=["#2A7B9B", "#57C785", "#28BF50"])
        fig2.update_coloraxes(showscale=False)
        fig2.update_traces(width=0.4, marker_cornerradius=8, hovertemplate="<b>%{y}</b><br>Active Players: %{x}<extra></extra>", marker_line_width=0)
        st.plotly_chart(style_canvas_chart(fig2, height=340), use_container_width=True, config={"displayModeBar": False})

    col3, col4 = st.columns([3, 2], gap="small")
    with col3:
        st.markdown("<h3 class='glass-header'>ATP vs WTA Points Range</h3>", unsafe_allow_html=True)
        if 'gender' in df_ranks.columns and 'points' in df_ranks.columns:
            box_df = df_ranks.copy()
            box_df['Tour'] = box_df['gender'].apply(
                lambda g: 'WTA' if clean_gender_value(g) == 'W' else 'ATP'
            )
            fig3 = px.box(
                box_df, x='Tour', y='points',
                color='Tour',
                color_discrete_map={'ATP': '#6C63FF', 'WTA': '#FF6B9D'},
                points='outliers',
                notched=True,
            )
            fig3.update_traces(
                marker_size=4,
                marker_opacity=0.6,
                line_width=2,
            )
            fig3.update_xaxes(title_text='Tour')
            fig3.update_yaxes(title_text='Points')
            st.plotly_chart(style_canvas_chart(fig3, height=240), use_container_width=True, config={"displayModeBar": False})

    with col4:
        st.markdown("<h3 class='glass-header'>Rank vs Points — Top 50</h3>", unsafe_allow_html=True)
        if 'rank' in df_ranks.columns and 'points' in df_ranks.columns:
            scatter_df = df_ranks.nsmallest(50, 'rank').copy()
            # Fill NaN movement then clip for colour scale readability
            scatter_df['movement'] = pd.to_numeric(scatter_df['movement'], errors='coerce').fillna(0).astype(int)
            scatter_df['movement_clipped'] = scatter_df['movement'].clip(-30, 30)
            fig4 = px.scatter(
                scatter_df,
                x='rank', y='points',
                color='movement_clipped',
                color_continuous_scale=['#EE5D50', '#B0BAD4', '#05CD99'],
                range_color=[-30, 30],
                hover_name='name',
                hover_data={'rank': True, 'points': True, 'movement': True, 'movement_clipped': False, 'country': True},
                size_max=14,
            )
            fig4.update_traces(
                marker=dict(size=10, opacity=0.85, line=dict(width=1, color='rgba(255,255,255,0.5)')),
                hovertemplate="<b>%{hovertext}</b><br>Rank: %{x}<br>Points: %{y:,}<br>Δ Movement: %{customdata[2]:+d}<extra></extra>",
            )
            fig4.update_coloraxes(
                colorbar=dict(
                    title='Δ Move',
                    tickvals=[-30, 0, 30],
                    ticktext=['↓ Drop', 'Stable', '↑ Rise'],
                    len=0.7,
                    thickness=10,
                )
            )
            fig4.update_xaxes(title_text='Rank', autorange='reversed')
            fig4.update_yaxes(title_text='Points')
            st.plotly_chart(style_canvas_chart(fig4, height=240), use_container_width=True, config={"displayModeBar": False})


    # =========================
    # ROW 3
    # =========================

    col5 = st.columns(1)[0]
    with col5: 
        st.markdown("<h3 class='glass-header'>Top Movers</h3>",unsafe_allow_html=True)
        movers = (df_ranks[pd.to_numeric(df_ranks["movement"],errors="coerce") > 0].copy())
        movers["movement"] = pd.to_numeric(movers["movement"],errors="coerce")
        movers = movers.nlargest(10, "movement")
        movers = movers.sort_values("movement")
        fig5 = px.bar(movers,x="movement",y="name",orientation="h",color="movement",color_continuous_scale=["#B0BAD4","#05CD99"])
        fig5.update_coloraxes(showscale=False)
        fig5.update_traces(marker_cornerradius=8,width=0.45,hovertemplate="<b>%{y}</b><br>Rise: +%{x}<extra></extra>")
        st.plotly_chart(style_canvas_chart(fig5, height=340),use_container_width=True,config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    



def render_podium_and_table(df_sorted: pd.DataFrame, key: str = "podium_grid"):
    """Render the top 3 podium and the challenger table using authentic database values."""
    if df_sorted.empty:
        st.info("No competitor records match the selected sidebar filters.")
        return
        
    p1 = df_sorted.iloc[0] if len(df_sorted) > 0 else None
    p2 = df_sorted.iloc[1] if len(df_sorted) > 1 else None
    p3 = df_sorted.iloc[2] if len(df_sorted) > 2 else None

    p2_html = ""
    if p2 is not None:
        p2_flag = country_code_to_flag(p2.get('country_code'))
        p2_gender_label = "Women" if clean_gender_value(p2.get('gender')) == "W" else "Men"
        p2_tour_label = "WTA" if clean_gender_value(p2.get('gender')) == "W" else "ATP"
        p2_html = f"""<div class="podium-card podium-2">
<div class="badge-medal medal-2">2</div>
<div style="font-size:1.3rem; font-weight:800; color:#2B3674; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{html.escape(p2['name'])}</div>
<div style="color:#707EAE; font-size:0.95rem; margin-top:0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{p2_flag} {html.escape(p2.get('country', 'N/A'))}</div>
<div style="font-size:1.15rem; font-weight:800; color:#2B3674; margin-top:0.6rem;">{p2.get('points', 0):,} Points</div>
<div style="margin-top:0.4rem; color:#707EAE; font-size:0.85rem; font-weight:600;">Movement: {p2.get('movement', 0):+d}</div>
<div><span class="tour-indicator" style="background:rgba(0, 82, 204, 0.1); color:#0052CC;">{p2_gender_label} • {p2_tour_label}</span></div>
</div>"""

    p1_html = ""
    if p1 is not None:
        p1_flag = country_code_to_flag(p1.get('country_code'))
        p1_gender_label = "Women" if clean_gender_value(p1.get('gender')) == "W" else "Men"
        p1_tour_label = "WTA" if clean_gender_value(p1.get('gender')) == "W" else "ATP"
        p1_html = f"""<div class="podium-card podium-1">
<div class="badge-medal medal-1">1</div>
<div style="font-size:1.45rem; font-weight:800; color:#2B3674; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{html.escape(p1['name'])}</div>
<div style="color:#707EAE; font-size:0.95rem; margin-top:0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{p1_flag} {html.escape(p1.get('country', 'N/A'))}</div>
<div style="font-size:1.3rem; font-weight:800; color:#2B3674; margin-top:0.6rem;">{p1.get('points', 0):,} Points</div>
<div style="margin-top:0.4rem; color:#707EAE; font-size:0.85rem; font-weight:600;">Movement: {p1.get('movement', 0):+d}</div>
<div><span class="tour-indicator" style="background:rgba(138, 43, 226, 0.1); color:#8A2BE2;">{p1_gender_label} • {p1_tour_label}</span></div>
</div>"""

    p3_html = ""
    if p3 is not None:
        p3_flag = country_code_to_flag(p3.get('country_code'))
        p3_gender_label = "Women" if clean_gender_value(p3.get('gender')) == "W" else "Men"
        p3_tour_label = "WTA" if clean_gender_value(p3.get('gender')) == "W" else "ATP"
        p3_html = f"""<div class="podium-card podium-3">
<div class="badge-medal medal-3">3</div>
<div style="font-size:1.3rem; font-weight:800; color:#2B3674; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{html.escape(p3['name'])}</div>
<div style="color:#707EAE; font-size:0.95rem; margin-top:0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{p3_flag} {html.escape(p3.get('country', 'N/A'))}</div>
<div style="font-size:1.15rem; font-weight:800; color:#2B3674; margin-top:0.6rem;">{p3.get('points', 0):,} Points</div>
<div style="margin-top:0.4rem; color:#707EAE; font-size:0.85rem; font-weight:600;">Movement: {p3.get('movement', 0):+d}</div>
<div><span class="tour-indicator" style="background:rgba(255, 20, 147, 0.1); color:#FF1493;">{p3_gender_label} • {p3_tour_label}</span></div>
</div>"""

    podium_html = f"""<div class="leaderboard-container">
    {p2_html}
    {p1_html}
    {p3_html}
</div>"""
    st.markdown(podium_html, unsafe_allow_html=True)
    
    table_rows = df_sorted.iloc[3:15].copy() if len(df_sorted) > 3 else pd.DataFrame()
    if not table_rows.empty:
        st.markdown("<h3 class='glass-header' style='margin-top:2.5rem; margin-bottom:1rem;'>Challenger Standings</h3>", unsafe_allow_html=True)
        
        table_rows["FlagCountry"] = table_rows.apply(
            lambda r: f"{country_code_to_flag(r.get('country_code'))} {r.get('country', 'N/A')}", axis=1
        )
        table_rows["Gender"] = table_rows["gender"].apply(lambda g: "Women" if clean_gender_value(g) == "W" else "Men")
        table_rows["Tour"] = table_rows["gender"].apply(lambda g: "WTA" if clean_gender_value(g) == "W" else "ATP")
        
        display_df = table_rows[["rank", "name", "Gender", "Tour", "FlagCountry", "points", "movement"]].rename(
            columns={
                "rank": "Rank", 
                "name": "Player Name", 
                "Gender": "Gender",
                "Tour": "Tour",
                "FlagCountry": "Country", 
                "points": "Points",
                "movement": "Movement"
            }
        )
        
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_default_column(sortable=True, filter=True, resizable=True)
        gb.configure_grid_options(rowHeight=42, headerHeight=45, suppressRowClickSelection=True)
        
        delta_style = JsCode("function(params) { if(params.value > 0){ return {'color':'#05CD99', 'fontWeight':'700'}; } if(params.value < 0){ return {'color':'#EE5D50', 'fontWeight':'700'}; } return {'color':'#707EAE', 'fontWeight':'600'}; }")
        gb.configure_column("Movement", cellStyle=delta_style, width=100)
        
        tour_style = JsCode("""
            function(params) {
                if (params.value === 'ATP') {
                    return {
                        'color': '#0052CC',
                        'fontWeight': '700',
                        'backgroundColor': 'rgba(0, 82, 204, 0.1)',
                        'borderRadius': '6px',
                        'textAlign': 'center'
                    };
                } else if (params.value === 'WTA') {
                    return {
                        'color': '#FF1493',
                        'fontWeight': '700',
                        'backgroundColor': 'rgba(255, 20, 147, 0.1)',
                        'borderRadius': '6px',
                        'textAlign': 'center'
                    };
                }
                return null;
            }
        """)
        gb.configure_column("Tour", cellStyle=tour_style, width=90)
        
        custom_css = {
            ".ag-root-wrapper": {"border": "none !important", "border-radius": "20px", "overflow": "hidden", "box-shadow": "0 10px 30px rgba(31,38,135,0.05)", "background-color": "rgba(255,255,255,0.45)", "backdrop-filter": "blur(20px)"},
            ".ag-header": {"background-color": "rgba(255,255,255,0.3) !important", "border-bottom": "1px solid rgba(255,255,255,0.6) !important"},
            ".ag-header-cell-label": {"color": "#707EAE !important", "font-weight": "600 !important", "font-size": "13px", "font-family": "'Poppins', sans-serif"},
            ".ag-row": {"font-size": "14px", "font-family": "'Poppins', sans-serif", "border-bottom": "1px solid rgba(255,255,255,0.4) !important", "background-color": "transparent !important", "color": "#2B3674 !important"},
            ".ag-row-hover": {"background-color": "rgba(255,255,255,0.6) !important"}
        }
        AgGrid(display_df, gridOptions=gb.build(), custom_css=custom_css, theme="alpine", fit_columns_on_grid_load=True, reload_data=False, allow_unsafe_jscode=True, key=key)

def render_leaderboards(df_ranks: pd.DataFrame):
    """Render the leaderboards page with Top Players, Most Points, and Most Improved tabs."""
    if df_ranks.empty:
        st.info("No competitor records found")
        return

    # Initialise tour selection in session state
    if "leaderboard_tour" not in st.session_state:
        st.session_state["leaderboard_tour"] = "ATP"

    tour_view = st.session_state["leaderboard_tour"]
    atp_active = tour_view == "ATP"
    wta_active = tour_view == "WTA"

    # ── Header row: title left, buttons right ─────────────────────────────────
    hdr_left, hdr_right = st.columns([5, 2], gap="small")
    with hdr_left:
        sub  = "ATP Tour · Men's Singles Rankings" if atp_active else "WTA Tour · Women's Singles Rankings"
        st.markdown(f"""
            <div style="padding: 0.75rem 0.25rem;">
                <div style="color:#2B3674; font-size:1.75rem; font-weight:800; letter-spacing:-0.03em; line-height:1.2; margin:0;"> {tour_view} Tour Standings</div>
                <div style="color:#707EAE; font-size:0.85rem; font-weight:500; margin-top:0.2rem;">{sub}</div>
            </div>
        """, unsafe_allow_html=True)

    with hdr_right:
        atp_col, wta_col = st.columns(2)
        with atp_col:
            atp_type = "primary" if atp_active else "secondary"
            if st.button("ATP", key="lb_atp_btn", use_container_width=True, type=atp_type):
                st.session_state["leaderboard_tour"] = "ATP"
                st.rerun()
        with wta_col:
            wta_type = "primary" if wta_active else "secondary"
            if st.button("WTA", key="lb_wta_btn", use_container_width=True, type=wta_type):
                st.session_state["leaderboard_tour"] = "WTA"
                st.rerun()

    # Re-read after potential rerun
    tour_view = st.session_state["leaderboard_tour"]
        
    # Variables update immediately without manual reruns
    atp_active = tour_view == "ATP"
    wta_active = tour_view == "WTA"

    # Re-read after potential rerun
    tour_view = st.session_state["leaderboard_tour"]

    # Filter leaderboard data based on selected Tour gender values
    if tour_view == "ATP":
        leaderboard_df = df_ranks[df_ranks["gender"].apply(clean_gender_value) == "M"]
    else:
        leaderboard_df = df_ranks[df_ranks["gender"].apply(clean_gender_value) == "W"]


    st.markdown("""
        <style>
        /* Tab container */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }

        /* Individual tab */
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding: 0 20px;
            border-radius: 8px 8px 0 0;
            color: #2B3674;
            font-weight: 600;
        }

        /* Selected tab */
        .stTabs [aria-selected="true"] {
            color: #2B3674;
        }
        </style>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Top Players", "Most Points", "Most Improved"])

    with tab1:
        # Sort by rank ascending (default official standings)
        df_sorted1 = leaderboard_df.sort_values(by=["rank", "name"], ascending=[True, True]).reset_index(drop=True)
        render_podium_and_table(df_sorted1, key=f"{tour_view}_top_players")

    with tab2:
        # Sort by total points descending
        df_sorted2 = leaderboard_df.sort_values(by=["points", "rank"], ascending=[False, True]).reset_index(drop=True)
        render_podium_and_table(df_sorted2, key=f"{tour_view}_most_points")

    with tab3:
        # Sort by rank movement descending (improvement)
        df_sorted3 = leaderboard_df.sort_values(by=["movement", "rank"], ascending=[False, True]).reset_index(drop=True)
        render_podium_and_table(df_sorted3, key=f"{tour_view}_most_improved")

def render_country_analysis(df_ranks: pd.DataFrame):
    """Render country-level distribution metrics, interactive statistics, and visual map overlays."""
    if df_ranks.empty:
        st.info("No competitor records found to populate the Country analysis node.")
        return

    # Extract list of unique countries available
    unique_countries = df_ranks.dropna(subset=["country", "country_code"]).drop_duplicates(subset=["country"])
    unique_countries = unique_countries.sort_values(by="country")
    
    if unique_countries.empty:
        st.info("No country records found.")
        return

    country_options = []
    country_to_display = {}
    display_to_country = {}
    
    for _, row in unique_countries.iterrows():
        name = row["country"]
        code = row["country_code"]
        flag = country_code_to_flag(code)
        disp = f"{flag} {name}"
        country_options.append(disp)
        country_to_display[name] = disp
        display_to_country[disp] = name

    # Two column layout: Left for Select/KPIs/Players, Right for Map
    col_left, col_right = st.columns([7, 5], gap="small")

    with col_left:
        st.markdown(f"<h3 class='glass-header glass-chart-card' style='font-weight:700'>Interactive Country Selector</h3>", unsafe_allow_html=True)
        selected_disp = st.selectbox("Select Target Country", country_options, label_visibility="collapsed")
        selected_country = display_to_country[selected_disp]

        country_players = df_ranks[df_ranks["country"] == selected_country].sort_values(by="rank")

        total_players = len(country_players)
        avg_rank = int(country_players["rank"].mean()) if total_players > 0 else 0
        total_points = int(country_players["points"].sum()) if total_players > 0 else 0

        # KPI metric cards inside left column
        kpi_sub1, kpi_sub2, kpi_sub3 = st.columns(3)
        sub_kpi_style = "padding:0px; display:flex; justify-content:center;align-items:center; flex-wrap:wrap"
        
        with kpi_sub1:
            st.markdown(f"""
            <div style="{sub_kpi_style}">
                <div style="color: {HEX_TEXT_MUTED}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; width:100%; text-align:center; ">
                <p style="color: {HEX_TEXT_MUTED}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin:0">Players</p>
                </div>
                <div style="color: {COLOR_PRIMARY}; font-size: 1.5rem; font-weight: 800; margin-top: 0.2rem;">{total_players}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_sub2:
            st.markdown(f"""
            <div style="{sub_kpi_style}">
                <div style="color: {HEX_TEXT_MUTED}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; width:100%; text-align:center; ">
                    <p style="color: {HEX_TEXT_MUTED}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin:0">Avg Rank</p>
                </div>
                <div style="color: {HEX_TEXT_MAIN}; font-size: 1.5rem; font-weight: 800; margin-top: 0.2rem;">#{avg_rank}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_sub3:
            st.markdown(f"""
            <div style="{sub_kpi_style}">
                <div style="color: {HEX_TEXT_MUTED}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; width:100%; text-align:center;">
                    <p style="color: {HEX_TEXT_MUTED}; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin:0">Total Points</p>
                </div>
                <div style="color: {HEX_TEXT_MAIN}; font-size: 1.5rem; font-weight: 800; margin-top: 0.2rem;">{total_points:,}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Player Listing for that country
        st.markdown(f"<h4 class='glass-header glass-chart-card' style='font-weight:500'>Competitors from {selected_country}</h4>", unsafe_allow_html=True)

        if not country_players.empty:
            country_players["Gender"] = country_players["gender"].apply(lambda g: "Women" if clean_gender_value(g) == "W" else "Men")
            country_players["Tour"] = country_players["gender"].apply(lambda g: "WTA" if clean_gender_value(g) == "W" else "ATP")

            display_players = country_players[["rank", "name", "Gender", "Tour", "points", "movement"]].rename(
                columns={"rank": "Rank", "name": "Competitor Name", "points": "Points", "movement": "Delta"}
            )

            gb = GridOptionsBuilder.from_dataframe(display_players)
            gb.configure_default_column(sortable=True, filter=True, resizable=True)
            gb.configure_grid_options(rowHeight=40, headerHeight=45, suppressRowClickSelection=True)
            gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)

            gb.configure_column("Rank", width=80)
            gb.configure_column("Competitor Name", width=180)
            gb.configure_column("Gender", width=100)
            gb.configure_column("Points", width=95)

            delta_style = JsCode("function(params) { if(params.value > 0){ return {'color':'#05CD99', 'fontWeight':'700'}; } if(params.value < 0){ return {'color':'#EE5D50', 'fontWeight':'700'}; } return {'color':'#707EAE', 'fontWeight':'600'}; }")
            gb.configure_column("Delta", cellStyle=delta_style, width=100)

            tour_style = JsCode("""
                function(params) {
                    if (params.value === 'ATP') {
                        return {
                            'color': '#0052CC',
                            'fontWeight': '700',
                            'backgroundColor': 'rgba(0, 82, 204, 0.1)',
                            'borderRadius': '6px',
                            'textAlign': 'center'
                        };
                    } else if (params.value === 'WTA') {
                        return {
                            'color': '#FF1493',
                            'fontWeight': '700',
                            'backgroundColor': 'rgba(255, 20, 147, 0.1)',
                            'borderRadius': '6px',
                            'textAlign': 'center'
                        };
                    }
                    return null;
                }
            """)
            gb.configure_column("Tour", cellStyle=tour_style, width=100)

            custom_css = {
                ".ag-root-wrapper": {"border": "none !important", "border-radius": "16px", "overflow": "hidden", "background-color": "rgba(255,255,255,0.45)", "backdrop-filter": "blur(20px)"},
                ".ag-header": {"background-color": "rgba(255,255,255,0.3) !important", "border-bottom": "1px solid rgba(255,255,255,0.6) !important"},
                ".ag-header-cell-label": {"color": "#707EAE !important", "font-weight": "600 !important", "font-size": "13px", "font-family": "'Poppins', sans-serif"},
                ".ag-row": {"font-size": "13px", "font-family": "'Poppins', sans-serif", "border-bottom": "1px solid rgba(255,255,255,0.4) !important", "background-color": "transparent !important", "color": "#2B3674 !important"},
                ".ag-row-hover": {"background-color": "rgba(255,255,255,0.6) !important"}
            }
            AgGrid(display_players, gridOptions=gb.build(), custom_css=custom_css, theme="alpine", height=270, fit_columns_on_grid_load=True, reload_data=False, allow_unsafe_jscode=True)
        else:
            st.info("No competitors found.")

    with col_right:

        # Header layout with Title and Style selector
        header_col = st.container()
        with header_col:
            st.markdown(f"<h3 class='glass-header glass-chart-card' style='font-weight:700'>Global Density Map</h3>", unsafe_allow_html=True)

        proj_map = {
                "3D Globe": "orthographic",
                "Natural Earth": "natural earth",
                "Flat Mercator": "mercator"
            }
        proj_disp = "Natural Earth"
        selected_proj = proj_map[proj_disp]

        # Build interactive Plotly Choropleth mapping player density
        map_data = df_ranks.groupby(["country", "country_code"]).size().reset_index(name="Players")

        fig = px.choropleth(
            map_data,
            locations="country_code",
            color="Players",
            hover_name="country",
            color_continuous_scale=["rgba(5, 205, 153, 0.15)", "rgba(5, 205, 153, 0.85)"],
            projection=selected_proj
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_showscale=False
        )

        fig.update_geos(
            showcoastlines=True, coastlinecolor="rgba(255,255,255,0.08)",
            showland=True, landcolor="rgba(15, 23, 42, 0.6)",
            showocean=True, oceancolor="rgba(15, 23, 42, 0.3)",
            showlakes=False,
            showcountries=True, countrycolor="rgba(255,255,255,0.1)",
            bgcolor="rgba(0,0,0,0)",
            projection_type=selected_proj
        )

        # Overlay bright neon cyan highlight for selected country
        selected_row = map_data[map_data["country"] == selected_country]
        if not selected_row.empty:
            highlight_trace = go.Choropleth(
                locations=selected_row["country_code"],
                z=[1],
                colorscale=[[0, "#00F0FF"], [1, "#00F0FF"]],
                showscale=False,
                hoverinfo="skip",
                marker=dict(
                    line=dict(color="#00F0FF", width=3.0),
                    opacity=0.95
                )
            )
            fig.add_trace(highlight_trace)

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Bottom Global Country Standings
    st.markdown(f"<h3 class='glass-header glass-chart-card-Custom' style='font-weight:700'>Global Country Standings</h3>", unsafe_allow_html=True)

    country_groups = []
    for c_name, group in df_ranks.groupby("country"):
        if group.empty:
            continue
        top_player_row = group.sort_values(by="rank").iloc[0]
        code = top_player_row.get("country_code", "")
        flag = country_code_to_flag(code)

        # Dominant gender for this country
        gender_counts = group["gender"].apply(clean_gender_value).value_counts()
        dominant_gender = gender_counts.index[0] if not gender_counts.empty else "M"
        gender_label = "Women" if dominant_gender == "W" else "Men"
        tour_label   = "WTA"   if dominant_gender == "W" else "ATP"

        country_groups.append({
            "Country": f"{flag} {c_name}",
            "Gender": gender_label,
            "Tour": tour_label,
            "Total Players": len(group),
            "Average Rank": int(group["rank"].mean()),
            "Total Points": int(group["points"].sum()),
            "Top Player": top_player_row["name"],
            "Top Player Rank": top_player_row["rank"]
        })

    if country_groups:
        df_global_country = pd.DataFrame(country_groups).sort_values(by="Total Players", ascending=False).reset_index(drop=True)

        gb = GridOptionsBuilder.from_dataframe(df_global_country)
        gb.configure_default_column(sortable=True, filter=True, resizable=True)
        gb.configure_grid_options(rowHeight=50, headerHeight=45, suppressRowClickSelection=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=12)

        bold_style = JsCode(f"function(params) {{ return {{'fontWeight':'700', 'color':'{HEX_TEXT_MAIN}'}}; }}")
        gb.configure_column("Total Players", cellStyle=bold_style, width=130)
        gb.configure_column("Total Points",  cellStyle=bold_style, width=130)

        gender_style = JsCode(f"function(params) {{ return {{'fontWeight':'600', 'color':'{HEX_TEXT_MAIN}'}}; }}")
        gb.configure_column("Gender", cellStyle=gender_style, width=100)

        tour_style = JsCode("""
            function(params) {
                if (params.value === 'ATP') {
                    return {
                        'color': '#0052CC',
                        'fontWeight': '700',
                        'backgroundColor': 'rgba(0, 82, 204, 0.1)',
                        'borderRadius': '6px',
                        'textAlign': 'center'
                    };
                } else if (params.value === 'WTA') {
                    return {
                        'color': '#FF1493',
                        'fontWeight': '700',
                        'backgroundColor': 'rgba(255, 20, 147, 0.1)',
                        'borderRadius': '6px',
                        'textAlign': 'center'
                    };
                }
                return null;
            }
        """)
        gb.configure_column("Tour", cellStyle=tour_style, width=90)

        custom_css = {
            ".ag-root-wrapper": {"border": "none !important", "border-radius": "20px", "overflow": "hidden", "box-shadow": "0 10px 30px rgba(31,38,135,0.05)", "background-color": "rgba(255,255,255,0.45)", "backdrop-filter": "blur(20px)"},
            ".ag-header": {"background-color": "rgba(255,255,255,0.3) !important", "border-bottom": "1px solid rgba(255,255,255,0.6) !important"},
            ".ag-header-cell-label": {"color": "#707EAE !important", "font-weight": "600 !important", "font-size": "13px", "font-family": "'Poppins', sans-serif"},
            ".ag-row": {"font-size": "14px", "font-family": "'Poppins', sans-serif", "border-bottom": "1px solid rgba(255,255,255,0.4) !important", "background-color": "transparent !important", "color": "#2B3674 !important"},
            ".ag-row-hover": {"background-color": "rgba(255,255,255,0.6) !important"}
        }
        AgGrid(df_global_country, gridOptions=gb.build(), custom_css=custom_css, theme="alpine", height=580, fit_columns_on_grid_load=True, reload_data=False, allow_unsafe_jscode=True)
    else:
        st.info("No competitor records found to group.")


def render_advanced_analytics(df_ranks: pd.DataFrame):

    search_input = st.text_input(
        "Search",
        placeholder="Search player...",
        label_visibility="collapsed",
    ).strip()
    filtered_df = df_ranks.copy()

    if search_input and "name" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["name"].str.contains(search_input, case=False, na=False, regex=False)]

    st.markdown(f"<div style='margin-bottom:14px; color:{HEX_TEXT_MUTED}; font-weight:600; font-size:15px;'>Returned {len(filtered_df):,} Matching Matrix Profiles</div>", unsafe_allow_html=True)

    if filtered_df.empty:
        st.info("No records found.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if "gender" in filtered_df.columns:
        filtered_df["Gender"] = filtered_df["gender"].apply(lambda g: "Women" if clean_gender_value(g) == "W" else "Men")
        filtered_df["Tour"] = filtered_df["gender"].apply(lambda g: "WTA" if clean_gender_value(g) == "W" else "ATP")

    cols_to_show = [c for c in ["Cleaned ID", "rank", "name", "Gender", "Tour", "country", "points", "movement", "competitions_played"] if c in filtered_df.columns]
    matrix_df = filtered_df[cols_to_show].rename(
        columns={
            "Cleaned ID": "ID Token", 
            "rank": "Official Rank", 
            "name": "Player Name", 
            "Gender": "Gender",
            "Tour": "Tour",
            "country": "Country", 
            "points": "Points", 
            "movement": "Delta", 
            "competitions_played": "Events"
        }
    )

    rank_style = JsCode(f"function(params) {{ return (params.value <= 3) ? {{'fontWeight':'700', 'color':'{COLOR_PRIMARY}'}} : {{'fontWeight':'600', 'color':'{HEX_TEXT_MAIN}'}}; }}")
    points_style = JsCode(f"function(params) {{ return {{'fontWeight':'700', 'color':'{COLOR_PRIMARY}'}}; }}")
    player_style = JsCode(f"function(params) {{ return {{'fontWeight':'600', 'color':'{HEX_TEXT_MAIN}'}}; }}")
    delta_style = JsCode("function(params) { if(params.value > 0){ return {'color':'#05CD99', 'fontWeight':'700'}; } if(params.value < 0){ return {'color':'#EE5D50', 'fontWeight':'700'}; } return {'color':'#707EAE', 'fontWeight':'600'}; }")
    gender_style = JsCode(f"function(params) {{ return {{'fontWeight':'600', 'color':'{HEX_TEXT_MAIN}'}}; }}")
    tour_style = JsCode("""
        function(params) {
            if (params.value === 'ATP') {
                return {
                    'color': '#0052CC',
                    'fontWeight': '700',
                    'backgroundColor': 'rgba(0, 82, 204, 0.1)',
                    'borderRadius': '6px',
                    'textAlign': 'center'
                };
            } else if (params.value === 'WTA') {
                return {
                    'color': '#FF1493',
                    'fontWeight': '700',
                    'backgroundColor': 'rgba(255, 20, 147, 0.1)',
                    'borderRadius': '6px',
                    'textAlign': 'center'
                };
            }
            return null;
        }
    """)

    gb = GridOptionsBuilder.from_dataframe(matrix_df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    if "Official Rank" in matrix_df.columns: gb.configure_column("Official Rank", cellStyle=rank_style, width=120)
    if "Player Name" in matrix_df.columns: gb.configure_column("Player Name", cellStyle=player_style, width=240)
    if "Gender" in matrix_df.columns: gb.configure_column("Gender", cellStyle=gender_style, width=110)
    if "Tour" in matrix_df.columns: gb.configure_column("Tour", cellStyle=tour_style, width=100)
    if "Points" in matrix_df.columns: gb.configure_column("Points", cellStyle=points_style, width=130)
    if "Delta" in matrix_df.columns: gb.configure_column("Delta", cellStyle=delta_style, width=100)
    
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
    gb.configure_grid_options(rowHeight=45, headerHeight=50, suppressRowClickSelection=True)

    custom_css = {
        ".ag-root-wrapper": {"border": "none !important", "border-radius": "24px", "overflow": "hidden", "box-shadow": "0 10px 30px rgba(31,38,135,0.08), inset 0 1px 0 rgba(255,255,255,0.9)", "background-color": "rgba(255,255,255,0.45)", "backdrop-filter": "blur(20px)"},
        ".ag-header": {"background-color": "rgba(255,255,255,0.3) !important", "border-bottom": "1px solid rgba(255,255,255,0.6) !important"},
        ".ag-header-cell": {"background-color": "transparent !important"},
        ".ag-header-cell-label": {"color": "#707EAE !important", "font-weight": "600 !important", "font-size": "13px", "font-family": "'Poppins', sans-serif"},
        ".ag-row": {"font-size": "14px", "font-family": "'Poppins', sans-serif", "border-bottom": "1px solid rgba(255,255,255,0.4) !important", "background-color": "transparent !important"},
        ".ag-row:nth-child(even)": {"background-color": "rgba(255,255,255,0.1) !important"},
        ".ag-row:nth-child(odd)": {"background-color": "rgba(255,255,255,0.3) !important"},
        ".ag-row-hover": {"background-color": "rgba(255,255,255,0.7) !important"}
    }
    AgGrid(matrix_df, gridOptions=gb.build(), custom_css=custom_css, theme="alpine", height=620, fit_columns_on_grid_load=True, allow_unsafe_jscode=True, reload_data=False)
    st.markdown('</div>', unsafe_allow_html=True)

def render_competitor_details(df_ranks: pd.DataFrame):
    if df_ranks.empty or "name" not in df_ranks.columns:
        st.warning("Adjust target sidebar parameters to reveal matching profiles.")
        return
        
    selected_player = st.selectbox("Search Competitor", df_ranks["name"].dropna().tolist())
    player_data = df_ranks[df_ranks["name"] == selected_player].iloc[0]
    
    p_name = html.escape(str(player_data.get('name', 'Unknown')))
    p_country = html.escape(str(player_data.get('country', 'N/A')))
    p_country_code = player_data.get('country_code', '')
    p_flag = country_code_to_flag(p_country_code)
    
    g_val = clean_gender_value(player_data.get('gender'))
    gender_label = "Women" if g_val == "W" else "Men"
    tour_label = "WTA" if g_val == "W" else "ATP"
    
    gender_color = "#FF1493" if g_val == "W" else "#0052CC"
    gender_bg = "rgba(255, 20, 147, 0.1)" if g_val == "W" else "rgba(0, 82, 204, 0.1)"
    
    tour_color = COLOR_PRIMARY
    tour_bg = "rgba(138, 43, 226, 0.1)"
    
    p_rank = player_data.get('rank', 'N/A')
    p_points = player_data.get('points', 0)
    p_movement = player_data.get('movement', 0)
    p_played = player_data.get('competitions_played', 0)
    
    avatar_seed = p_name.replace(" ", "").replace(",", "")
    avatar_url = f"https://api.dicebear.com/7.x/notionists/svg?seed={avatar_seed}"

    try:
        p_movement_int = int(p_movement)
        delta_color = "#05CD99" if p_movement_int >= 0 else "#EE5D50"
        delta_prefix = "+" if p_movement_int > 0 else ""
        delta_text = f"{delta_prefix}{p_movement_int}" if p_movement_int != 0 else "-"
    except ValueError:
        delta_color = "#707EAE"
        delta_text = "-"

    html_string = f"""<div style="background: transparent; margin-bottom: 0rem;">
<div style="display: flex; gap: 2.5rem; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.7); padding-bottom: 2.5rem; margin-bottom: 2.5rem;">
<img src="{avatar_url}" style="width: 150px; height: 150px; border-radius: 50%; background: rgba(255,255,255,0.6); border: 4px solid {COLOR_PRIMARY}; object-fit: cover; box-shadow: 0px 10px 25px rgba(138, 43, 226, 0.1);"/>
<div style="flex-grow: 1;">
<div style="display: flex; justify-content: space-between; align-items: flex-start;">
<div>
<div style="color: {COLOR_PRIMARY}; font-size: 1rem; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 800; margin-bottom: 0.5rem;">Official Competitor Profile</div>
<div style="color: {HEX_TEXT_MAIN}; font-size: 2.8rem; font-weight: 800; line-height: 1.1;">{p_name}</div>
<div style="color: {HEX_TEXT_MUTED}; font-size: 1.1rem; font-weight: 600; display: flex; align-items: center; gap: 14px; margin-top: 0.8rem;">
    <span>{p_flag} {p_country}</span>
    <span style="background: {gender_bg}; color: {gender_color}; padding: 4px 12px; border-radius: 8px; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.5px;">{gender_label}</span>
    <span style="background: {tour_bg}; color: {tour_color}; padding: 4px 12px; border-radius: 8px; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.5px;">{tour_label} Tour</span>
</div>
</div>
<div style="text-align: right; background: rgba(255,255,255,0.6); padding: 1.2rem 2.5rem; border-radius: 20px; border: none; box-shadow: 0 4px 15px rgba(31,38,135,0.02), inset 0 1px 0 rgba(255,255,255,0.9);">
<div style="color: {HEX_TEXT_MUTED}; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.2rem;">Current Rank</div>
<div style="color: {COLOR_PRIMARY}; font-size: 3.5rem; font-weight: 800; line-height: 1;">#{p_rank}</div>
</div>
</div>
</div>
</div>
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem;">
<div style="background: rgba(255, 255, 255, 0.6); padding: 2rem; border-radius: 20px; text-align: center; border: none; box-shadow: 0 4px 15px rgba(31,38,135,0.02), inset 0 1px 0 rgba(255,255,255,0.9);">
<div style="color: {HEX_TEXT_MUTED}; font-size: 1.05rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.8rem;">Total Ranking Points</div>
<div style="color: {HEX_TEXT_MAIN}; font-size: 2.5rem; font-weight: 800;">{p_points:,}</div>
</div>
<div style="background: rgba(255, 255, 255, 0.6); padding: 2rem; border-radius: 20px; text-align: center; border: none; box-shadow: 0 4px 15px rgba(31,38,135,0.02), inset 0 1px 0 rgba(255,255,255,0.9);">
<div style="color: {HEX_TEXT_MUTED}; font-size: 1.05rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.8rem;">Rank Movement</div>
<div style="color: {delta_color}; font-size: 2.5rem; font-weight: 800;">{delta_text}</div>
</div>
<div style="background: rgba(255, 255, 255, 0.6); padding: 2rem; border-radius: 20px; text-align: center; border: none; box-shadow: 0 4px 15px rgba(31,38,135,0.02), inset 0 1px 0 rgba(255,255,255,0.9);">
<div style="color: {HEX_TEXT_MUTED}; font-size: 1.05rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.8rem;">Tournaments Played</div>
<div style="color: {HEX_TEXT_MAIN}; font-size: 2.5rem; font-weight: 800;">{p_played}</div>
</div>
</div>
</div>"""
    st.markdown(html_string, unsafe_allow_html=True)

def init_session_state():
    defaults = {
        "country": "All Countries",
        "gender": "All",
        "tour": "All",
        "year": "All Years",
    }
    for key, val in defaults.items():
        state_key = f"filter_{key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = val

def execute_state_purge():
    st.session_state["filter_country"] = "All Countries"
    st.session_state["filter_gender"]  = "All"
    st.session_state["filter_tour"]    = "All"
    st.session_state["filter_year"]    = "All Years"

def main():
    init_interface()
    init_session_state()
    
    df_comps = get_competitions()
    df_ranks = get_competitors()
    
    if not df_ranks.empty and "competitor_id" in df_ranks.columns:
        df_ranks["Cleaned ID"] = df_ranks["competitor_id"].astype(str).str.replace("sr:competitor:", "", regex=False)
    else:
        df_ranks["Cleaned ID"] = ""
        
    # ── NAV PAGES CONFIG ───────────────────────────────────────────────────────
    NAV_PAGES = [
        ("Dashboard Overview",    ":material/dashboard:"),
        ("Advanced Search Matrix", ":material/search:"),
        ("Country Wise Analysis",  ":material/public:"),
        ("Competitor Profile",     ":material/person:"),
        ("Leaderboards",           ":material/leaderboard:"),
    ]

    if "active_view" not in st.session_state:
        st.session_state["active_view"] = "Dashboard Overview"

    with st.sidebar:
        col1, col2 = st.columns([1, 4])

        with col1:
            st.image("assets/logo.png", width=50)

        with col2:
            st.markdown("""
            <div style="padding-top:2px;">
                <div class="brand-title">Tennis</div>
                <div class="brand-sub">Analytics</div>
            </div>
            """, unsafe_allow_html=True)

        # Orphaned <div> wrappers removed — Streamlit does not nest widget
        # output inside preceding st.markdown() open-tags, so those divs
        # never become real DOM parents.  The sidebar-wide CSS selectors
        # (anchored to [data-testid="stSidebar"]) handle styling instead.
        st.button("⟳  Reset Filters", on_click=execute_state_purge, key="reset_btn")

        # ── NAVIGATION ────────────────────────────────────────────────────────
        st.markdown("""
        <div class='sidebar-section-heading'>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8A7FBE" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
            NAVIGATION
        </div>
        """, unsafe_allow_html=True)

        for page_name, page_icon in NAV_PAGES:
            is_active = st.session_state["active_view"] == page_name
            btn_type = "primary" if is_active else "secondary"
            if st.button(
                f"{page_icon}  {page_name}",
                key=f"nav_{page_name}",
                use_container_width=True,
                type=btn_type,
            ):
                st.session_state["active_view"] = page_name
                st.rerun()

        active_view_target = st.session_state["active_view"]

        st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

        # ── FILTERS SECTION ───────────────────────────────────────────────────
        st.markdown("""
        <div class='sidebar-section-heading'>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8A7FBE" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
            </svg>
            FILTERS
        </div>
        """, unsafe_allow_html=True)

        # Gender toggle: Men / Women / All
        st.markdown("<div class='filter-label'>Gender</div>", unsafe_allow_html=True)
        gender_cols = st.columns(3)
        gender_options = ["Men", "Women", "All"]
        for idx, g_opt in enumerate(gender_options):
            with gender_cols[idx]:
                is_sel = st.session_state.get("filter_gender", "All") == g_opt
                btn_style = "primary" if is_sel else "secondary"
                if st.button(g_opt, key=f"gender_btn_{g_opt}", use_container_width=True, type=btn_style):
                    st.session_state["filter_gender"] = g_opt
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Country dropdown
        st.markdown("<div class='filter-label'>Country</div>", unsafe_allow_html=True)
        if "country" in df_ranks.columns:
            country_list = ["All Countries"] + sorted(df_ranks["country"].dropna().unique().tolist())
        else:
            country_list = ["All Countries"]
        cur_country = st.session_state.get("filter_country", "All Countries")
        if cur_country not in country_list:
            cur_country = "All Countries"
        st.selectbox("Country", country_list,
                     index=country_list.index(cur_country),
                     key="filter_country",
                     label_visibility="collapsed")

    selected_country = st.session_state.get("filter_country", "All Countries")
    selected_gender  = st.session_state.get("filter_gender",  "All")
    selected_tour    = st.session_state.get("filter_tour",    "All")

    filtered_ranks = df_ranks.copy()
    filtered_comps = df_comps.copy()

    selected_type = st.session_state.get(
        "filter_type",
        "All Types"
    )
    selected_tournament = st.session_state.get(
        "filter_tournament",
        "All Tournaments"
    )
    if not filtered_comps.empty:
        if selected_type != "All Types":
            filtered_comps = filtered_comps[
            filtered_comps["type"] == selected_type
        ]

    if selected_tournament != "All Tournaments":
        filtered_comps = filtered_comps[
            filtered_comps["competition_name"] == selected_tournament
        ]

    if not filtered_ranks.empty:
        # Country filter
        if selected_country != "All Countries" and "country" in filtered_ranks.columns:
            filtered_ranks = filtered_ranks[filtered_ranks["country"] == selected_country]

        # Tour / Gender filter (Tour takes priority; Gender is alias)
        if selected_tour == "ATP":
            filtered_ranks = filtered_ranks[filtered_ranks["gender"].apply(clean_gender_value) == "M"]
        elif selected_tour == "WTA":
            filtered_ranks = filtered_ranks[filtered_ranks["gender"].apply(clean_gender_value) == "W"]
        else:
            # Apply gender toggle if tour is "All"
            if selected_gender == "Men" and "gender" in filtered_ranks.columns:
                filtered_ranks = filtered_ranks[filtered_ranks["gender"].apply(clean_gender_value) == "M"]
            elif selected_gender == "Women" and "gender" in filtered_ranks.columns:
                filtered_ranks = filtered_ranks[filtered_ranks["gender"].apply(clean_gender_value) == "W"]

        # Sort by rank
        if "rank" in filtered_ranks.columns:
            filtered_ranks = filtered_ranks.sort_values("rank", ascending=True)

    total_competitors_audited = filtered_ranks['Cleaned ID'].nunique() if not filtered_ranks.empty else 0
    total_competitions_loaded = filtered_comps['competition_id'].nunique() if ('competition_id' in filtered_comps.columns and not filtered_comps.empty) else 0
    mean_points_balance = int(filtered_ranks['points'].mean()) if (not filtered_ranks.empty and "points" in filtered_ranks.columns and pd.api.types.is_numeric_dtype(filtered_ranks['points'])) else 0
    total_represented_countries = filtered_ranks['country'].nunique() if ('country' in filtered_ranks.columns and not filtered_ranks.empty) else 0

    st.markdown(f"""
        <div style='margin-bottom: 1.5rem;'>
            <h1 style='font-size: 2.1rem; font-weight: 700; color: #2B3674; margin: 0;'>{active_view_target}</h1>
            <p style='color: #707EAE; margin: 0.1rem 0 1rem 0; font-size: 0.95rem;'>Real-time insights into the global tennis ecosystem</p>
        </div>
    """, unsafe_allow_html=True)
    
    kpi_slots = st.columns(4)
    kpi_style = "padding: 1.1rem 1.25rem; display: flex; align-items: center; gap: 1rem;"
    
    with kpi_slots[0]:
        st.markdown(f"""
        <div style="{kpi_style}">
            <div style="background: rgba(138, 43, 226, 0.1); width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; color: #8A2BE2;">👥</div>
            <div>
                <div style="color: #A3AED0; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Total Competitors</div>
                <div style="color: #2B3674; font-size: 1.6rem; font-weight: 800; line-height: 1.1; margin-top:0.1rem; margin-bottom:0.5rem;">{total_competitors_audited:,}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with kpi_slots[1]:
        st.markdown(f"""
        <div style="{kpi_style}">
            <div style="background: rgba(255, 154, 68, 0.1); width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; color: #FF9A44;">🏆</div>
            <div>
                <div style="color: #A3AED0; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Total Competitions</div>
                <div style="color: #2B3674; font-size: 1.6rem; font-weight: 800; line-height: 1.1; margin-top:0.1rem; margin-bottom:0.5rem;">{total_competitions_loaded:,}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with kpi_slots[2]:
        st.markdown(f"""
        <div style="{kpi_style}">
            <div style="background: rgba(234, 128, 252, 0.15); width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; color: #EA80FC;">📈</div>
            <div>
                <div style="color: #A3AED0; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Avg Ranking Points</div>
                <div style="color: #2B3674; font-size: 1.6rem; font-weight: 800; line-height: 1.1; margin-top:0.1rem; margin-bottom:0.5rem;">{mean_points_balance:,}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with kpi_slots[3]:
        st.markdown(f"""
        <div style="{kpi_style}">
            <div style="background: rgba(29, 250, 241, 0.1); width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; color: #00B4DB;">🌐</div>
            <div>
                <div style="color: #A3AED0; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Countries Represented</div>
                <div style="color: #2B3674; font-size: 1.6rem; font-weight: 800; line-height: 1.1; margin-top:0.1rem;">{total_represented_countries}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)

    if "Dashboard Overview" == active_view_target:
        render_dashboard(filtered_comps, filtered_ranks)
    elif "Advanced Search Matrix" == active_view_target:
        render_advanced_analytics(filtered_ranks)
    elif "Country Wise Analysis" == active_view_target:
        render_country_analysis(filtered_ranks)
    elif "Leaderboards" == active_view_target:
        render_leaderboards(filtered_ranks)
    elif "Competitor Profile" == active_view_target:
        render_competitor_details(filtered_ranks)

if __name__ == "__main__":
    main()