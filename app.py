import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF
from datetime import datetime
import tempfile
import os
from decimal import Decimal, getcontext
import math
import pathlib
import re
import io
import uuid

# === PAGE CONFIG ===
st.set_page_config(page_title="Fuel EU GHG Calculator", layout="wide")

# === CONSTANTS & CONFIGURATION ===
BASE_TARGET = 91.16
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.145, 2040: 0.31, 2045: 0.62, 2050: 0.80}
PENALTY_RATE = 2400  # EUR per tonne of VLSFO-equivalent energy shortfall
VLSFO_ENERGY_CONTENT = 41_000  # MJ/t
REWARD_FACTOR_RFNBO_MULTIPLIER = 2
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273},}

# --- CUSTOM FUELS SESSION SCAFFOLD ---
DEFAULT_CF = {
    "name": "Custom fuel",
    "qty_t": 0.0,
    "price_usd": 0.0,
    "lcv": 0.0000,
    "rfnbo": False,
    "mode": "Basic",         # "Basic" or "Advanced"
    "wtw": 0.00,            # used only in Basic mode (gCO2e/MJ)
    "wtt": 0.0,             # used only in Advanced mode (gCO2e/MJ)
    "ttw_co2": 0.000,        # g/g fuel
    "ttw_ch4": 0.0,          # g/g fuel
    "ttw_n2o": 0.0,          # g/g fuel
    "ch4_slip": 0.0,         # g CH4 / MJ
}
if "custom_fuels" not in st.session_state:
    st.session_state.custom_fuels = [] # list of dicts like DEFAULT_CF

# === FUEL DATABASE ===
FUELS = [
    {"name": "Heavy Fuel Oil (HFO)",                                                                    "lcv": 0.0405,  "wtt": 13.5,  "ttw_co2": 3.114,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Low Sulphur Fuel Oil (LSFO)",                                                             "lcv": 0.0405,  "wtt": 13.7,  "ttw_co2": 3.114,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)",                                                       "lcv": 0.041,   "wtt": 13.2,  "ttw_co2": 3.206,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Ultra Low Sulphur Fuel Oil (ULSFO)",                                                      "lcv": 0.0405,  "wtt": 13.2,  "ttw_co2": 3.114,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Low Fuel Oil (LFO)",                                                                      "lcv": 0.041,   "wtt": 13.2,  "ttw_co2": 3.151,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Marine Diesel/Gas Oil (MDO/MGO)",                                                         "lcv": 0.0427,  "wtt": 14.4,  "ttw_co2": 3.206,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Liquefied Natural Gas (LNG Otto dual fuel medium speed)",                                 "lcv": 0.0491,  "wtt": 18.5,  "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":3.1},
    {"name": "Liquefied Natural Gas (LNG Otto dual fuel slow speed)",                                   "lcv": 0.0491,  "wtt": 18.5,  "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":1.7},
    {"name": "Liquefied Natural Gas (LNG Diesel dual fuel slow speed)",                                 "lcv": 0.0491,  "wtt": 18.5,  "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":0.2},
    {"name": "Liquefied Natural Gas (LNG LBSI)",                                                        "lcv": 0.0491,  "wtt": 18.5,  "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":2.6},
    {"name": "Liquefied Petroleum Gas (LPG propane)",                                                   "lcv": 0.0460,  "wtt": 7.8,   "ttw_co2": 3.000,  "ttw_ch4": 0.007,    "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Liquefied Petroleum Gas (LPG butane)",                                                    "lcv": 0.0460,  "wtt": 7.8,   "ttw_co2": 3.030,  "ttw_ch4": 0.007,    "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Fossil Hydrogen (H2)",                                                                    "lcv": 0.12,    "wtt": 132,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Fossil Ammonia (NH3)",                                                                    "lcv": 0.0186,  "wtt": 121,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Fossil Methanol",                                                                         "lcv": 0.0199,  "wtt": 31.3,  "ttw_co2": 1.375,  "ttw_ch4": 0.003,    "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Rapeseed Oil,B100)",                                                           "lcv": 0.0372,  "wtt": 50.1,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Wheat Straw,B100)",                                                            "lcv": 0.0372,  "wtt": 15.7,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (UCO,B20)",                                                                     "lcv": 0.03984, "wtt": 13.78, "ttw_co2": 2.4912, "ttw_ch4": 0.00004,  "ttw_n2O": 0.000144, "rfnbo": False},
    {"name": "Biodiesel (UCO,B24)",                                                                     "lcv": 0.03971, "wtt": 13.836,"ttw_co2": 2.36664,"ttw_ch4": 0.000038, "ttw_n2O": 0.0001368,"rfnbo": False},
    {"name": "Biodiesel (UCO,B30)",                                                                     "lcv": 0.03951, "wtt": 13.92, "ttw_co2": 2.1798, "ttw_ch4": 0.000035, "ttw_n2O": 0.000126, "rfnbo": False},
    {"name": "Biodiesel (UCO,B65)",                                                                     "lcv": 0.03836, "wtt": 14.41, "ttw_co2": 1.0899, "ttw_ch4": 0.0000175,"ttw_n2O": 0.000063, "rfnbo": False},
    {"name": "Biodiesel (UCO,B80)",                                                                     "lcv": 0.03786, "wtt": 14.62, "ttw_co2": 0.6228, "ttw_ch4": 0.00001,  "ttw_n2O": 0.000036, "rfnbo": False},
    {"name": "Biodiesel (UCO,B100)",                                                                    "lcv": 0.0372,  "wtt": 14.9,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (FAME,B100)",                                                                   "lcv": 0.0372,  "wtt": 16.65869,"ttw_co2": 0.0,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (FAME,B24)",                                                                    "lcv": 0.03971, "wtt": 13.836,"ttw_co2": 2.3075, "ttw_ch4": 0.000038, "ttw_n2O": 0.0001368,"rfnbo": False},
    {"name": "Biodiesel (waste wood Fischer-Tropsch diesel,B100)",                                      "lcv": 0.0372,  "wtt": 13.7,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (farmed wood Fischer-Tropsch diesel,B100)",                                     "lcv": 0.0372,  "wtt": 16.7,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Fischer-Tropsch diesel from black liquor gasification,B100)",                  "lcv": 0.0372,  "wtt": 10.2,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Animal Fats,B100)",                                                            "lcv": 0.0372,  "wtt": 20.8,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Sunflower Oil,B100)",                                                          "lcv": 0.0372,  "wtt": 44.7,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Soybean Oil,B100)",                                                            "lcv": 0.0372,  "wtt": 47.0,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Palm Oil from open effluent pond,B100)",                                       "lcv": 0.0372,  "wtt": 75.7,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Biodiesel (Palm Oil, process with methane capture at oil mill,B100)",                     "lcv": 0.0372,  "wtt": 51.6,  "ttw_co2": 2.834,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Sugar Beet,E100)",                                                            "lcv": 0.0268,  "wtt": 38.2,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Maize,E100)",                                                                 "lcv": 0.0268,  "wtt": 56.8,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Other cereals excluding maize,E100)",                                         "lcv": 0.0268,  "wtt": 58.5,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Wheat,E100)",                                                                 "lcv": 0.0268,  "wtt": 15.7,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bioethanol (Sugar Cane,E100)",                                                            "lcv": 0.0268,  "wtt": 28.6,  "ttw_co2": 1.913,  "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (Rape Seed,HVO100)",                                           "lcv": 0.0440,  "wtt": 50.1,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (Sunflower,HVO100)",                                           "lcv": 0.0440,  "wtt": 43.6,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},    
    {"name": "Hydrotreated Vegetable Oil (Soybean,HVO100)",                                             "lcv": 0.0440,  "wtt": 46.5,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},  
    {"name": "Hydrotreated Vegetable Oil (Palm Oil from open effluent pond,HVO100)",                    "lcv": 0.0440,  "wtt": 73.3,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (Palm Oil, process with methane capture at oil mill,HVO100)",  "lcv": 0.0440,  "wtt": 48.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (UCO,HVO100)",                                                 "lcv": 0.0440,  "wtt": 16.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (Animal Fats,HVO100)",                                         "lcv": 0.0440,  "wtt": 21.8,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Straight Vegetable Oil (Rape Seed,SVO100)",                                               "lcv": 0.0440,  "wtt": 40.0,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},
    {"name": "Straight Vegetable Oil (Sunflower,SVO100)",                                               "lcv": 0.0440,  "wtt": 34.3,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},    
    {"name": "Straight Vegetable Oil (Soybean,SVO100)",                                                 "lcv": 0.0440,  "wtt": 36.9,  "ttw_co2": 3.115,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": False},  
    {"name": "Straight Vegetable Oil (Palm Oil from open effluent pond,SVO100)",                        "lcv": 0.0440,  "wtt": 65.4,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Straight Vegetable Oil (Palm Oil, process with methane capture at oil mill,SVO100)",      "lcv": 0.0440,  "wtt": 57.2,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Straight Vegetable Oil (UCO ,SVO100)",                                                    "lcv": 0.0440,  "wtt": 2.2,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bio-LNG (Otto dual fuel medium speed)",                                                   "lcv": 0.0491,  "wtt": 14.1,  "ttw_co2": 2.75,   "ttw_ch4": 0.14,     "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":3.1},
    {"name": "Bio-LNG (Otto dual fuel slow speed)",                                                     "lcv": 0.0491,  "wtt": 14.1,  "ttw_co2": 2.75,   "ttw_ch4": 0.14,     "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":1.7},
    {"name": "Bio-LNG (Diesel dual fuel slow speed)",                                                   "lcv": 0.0491,  "wtt": 14.1,  "ttw_co2": 2.75,   "ttw_ch4": 0.14,     "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":0.2},
    {"name": "Bio-LNG (LBSI)",                                                                          "lcv": 0.0491,  "wtt": 14.1,  "ttw_co2": 2.75,   "ttw_ch4": 0.14,     "ttw_n2O": 0.00011,  "rfnbo": False, "ch4_slip":2.6},
    {"name": "Bio-Hydrogen",                                                                            "lcv": 0.12,    "wtt": 0.0,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bio-Methanol (waste wood methanol)",                                                      "lcv": 0.0199,  "wtt": 13.5,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bio-Methanol (farmed wood methanol)",                                                     "lcv": 0.0199,  "wtt": 16.2,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "Bio-Methanol (from black-liquor gasification)",                                           "lcv": 0.0199,  "wtt": 10.4,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": False},
    {"name": "E-Methanol",                                                                              "lcv": 0.0199,  "wtt": 1.0,   "ttw_co2": 1.375,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": True},
    {"name": "E-Diesel",                                                                                "lcv": 0.0427,  "wtt": 1.0,   "ttw_co2": 3.206,  "ttw_ch4": 0.00005,  "ttw_n2O": 0.00018,  "rfnbo": True},
    {"name": "E-LNG (Otto dual fuel medium speed)",                                                     "lcv": 0.0491,  "wtt": 1.0,   "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": True, "ch4_slip":3.1 },
    {"name": "E-LNG (Otto dual fuel slow speed)",                                                       "lcv": 0.0491,  "wtt": 1.0,   "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": True, "ch4_slip":1.7},
    {"name": "E-LNG (Diesel dual fuel slow speed)",                                                     "lcv": 0.0491,  "wtt": 1.0,   "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": True, "ch4_slip":0.2},
    {"name": "E-LNG (LBSI)",                                                                            "lcv": 0.0491,  "wtt": 1.0,   "ttw_co2": 2.750,  "ttw_ch4": 0.0,      "ttw_n2O": 0.00011,  "rfnbo": True, "ch4_slip":2.6},
    {"name": "E-Hydrogen",                                                                              "lcv": 0.1200,  "wtt": 3.6,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": True},
    {"name": "E-Ammonia",                                                                               "lcv": 0.0186,  "wtt": 0.0,   "ttw_co2": 0.0,    "ttw_ch4": 0.0,      "ttw_n2O": 0.0,      "rfnbo": True},]

# === HELPERS ===
def target_intensity(year: int) -> float:
    if year <= 2020:
        return BASE_TARGET
    if year <= 2029:
        return BASE_TARGET * (1 - REDUCTIONS[2025])
    if year <= 2034:
        return BASE_TARGET * (1 - REDUCTIONS[2030])
    if year <= 2039:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    if year <= 2044:
        return BASE_TARGET * (1 - REDUCTIONS[2040])
    if year <= 2049:
        return BASE_TARGET * (1 - REDUCTIONS[2045])
    return BASE_TARGET * (1 - REDUCTIONS[2050])


def default_phase_in_pct(year: int) -> int:
    # EU ETS maritime phase-in: 2024:40%, 2025:70%, 2026+:100%. Years before ETS -> 0 by default
    if year <= 2024:
        return 0
    if year == 2025:
        return 70
    return 100


def compute_ets_cost(ttw_co2_g: Decimal, ttw_nonco2_g: Decimal, price_eur_per_t: float,
                      effective_coverage_pct: float, phase_in_pct: float, include_nonco2: bool):
    """Return (cost_eur, covered_tonnes). ETS is TtW-only. CH4+N2O+slip included from 2026+ if include_nonco2 is True."""
    ttw_for_ets = ttw_co2_g + (ttw_nonco2_g if include_nonco2 else Decimal("0"))
    covered_g = ttw_for_ets * Decimal(str(effective_coverage_pct / 100.0)) * Decimal(str(phase_in_pct / 100.0))
    covered_tonnes = float(covered_g / Decimal("1000000"))
    return covered_tonnes * float(price_eur_per_t), covered_tonnes

# === README FILE ===
if "show_readme" not in st.session_state:
    st.session_state.show_readme = False

def _open_readme():
    st.session_state.show_readme = True

def _close_readme():
    st.session_state.show_readme = False

with st.sidebar:
    st.markdown("📖 Help")
    col_a, col_b = st.columns(2)
    with col_a:
        st.button("Open README", on_click=_open_readme, use_container_width=True)
    with col_b:
        st.button("✖ Close", on_click=_close_readme, use_container_width=True)
    st.markdown("---")  # optional divider

# Render README in the main page when toggled on
if st.session_state.show_readme:
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_text = f.read()
    except Exception:
        readme_text = "_README.md not found in app directory._"
    st.markdown(readme_text, unsafe_allow_html=False)

# === STABLE RESET HANDLER ===
def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["trigger_reset"] = False

if st.session_state.get("trigger_reset", False):
    reset_app()

st.sidebar.button("🔁 Reset Calculator", on_click=lambda: st.session_state.update({"trigger_reset": True}))

# === SIDEBAR INPUTS ===
st.title("Fuel EU - GHG Intensity & Penalty Calculator")
st.sidebar.info("Enter fuel prices in USD & provide exchange rate.")

# Fuel pickers
fuel_inputs = {}
fuel_price_inputs = {}
initial_fuels = [
    f["name"]
    for f in FUELS
    if (not f["rfnbo"]) and ("Bio" not in f["name"]) and ("Biodiesel" not in f["name"]) and ("E-" not in f["name"]) and ("Vegetable" not in f["name"]) and ("SVO" not in f["name"]) and ("HVO" not in f["name"]) and ("Bio-" not in f["name"])  # keep purely fossil
]
mitigation_fuels = [f["name"] for f in FUELS if ("Bio" in f["name"]) or ("Biodiesel" in f["name"]) or ("Vegetable" in f["name"]) or f["rfnbo"] or ("E-" in f["name"]) or ("HVO" in f["name"]) or ("SVO" in f["name"]) ]
alternative_fuels = mitigation_fuels  # alias used below

categories = {
    "Fossil": [f for f in FUELS if f in [x for x in FUELS if x["name"] in initial_fuels]],
    "Bio": [f for f in FUELS if ("Bio" in f['name']) or ("Biodiesel" in f['name']) or ("Vegetable" in f['name']) or ("HVO" in f['name']) or ("SVO" in f['name'])],
    "RFNBO": [f for f in FUELS if f['rfnbo'] or ("E-" in f['name'])],
}

for category, fuels_in_cat in categories.items():
    with st.sidebar.expander(f"{category} Fuels", expanded=False):
        selected_fuels = st.multiselect(f"Select {category} Fuels", [f["name"] for f in fuels_in_cat], key=f"multiselect_{category}")
        for selected_fuel in selected_fuels:
            qty = st.number_input(f"{selected_fuel} (t)", min_value=0.0, step=1.0, value=0.0, format="%0.0f", key=f"qty_{selected_fuel}")
            fuel_inputs[selected_fuel] = qty
            price = st.number_input(
                f"{selected_fuel} - Price (USD/t)",
                min_value=0.0,
                value=0.0,
                step=10.0,
                format="%0.0f",
                key=f"price_{selected_fuel}",)
            fuel_price_inputs[selected_fuel] = price

# === CUSTOM FUEL (optional) ===
if "custom_fuels" not in st.session_state:
    st.session_state["custom_fuels"] = []

def _new_custom_fuel():
    return {
        "id": f"cf_{uuid.uuid4().hex[:8]}",
        "name": "Custom fuel",
        "qty_t": 0.0,
        "price_usd": 0.0,
        "lcv": 0.0000,
        "rfnbo": False,
        "mode": "Basic",
        "wtw": 0.00,  
        "wtt": 0.0,
        "ttw_co2": 0.000,
        "ttw_ch4": 0.0,
        "ttw_n2o": 0.0,
        "ch4_slip": 0.0,
    }

with st.sidebar.expander("Custom Fuel (optional)", expanded=False):
    # If empty, start with one row (no top-level Add button)
    if not st.session_state["custom_fuels"]:
        st.session_state["custom_fuels"].append(_new_custom_fuel())

    # Top-right "Clear all"
    _, col_right = st.columns([1, 1])
    with col_right:
        if st.button("🧹 Clear all", key="btn_clear_custom", use_container_width=True):
            st.session_state["custom_fuels"].clear()
            st.session_state["custom_fuels"].append(_new_custom_fuel())
            st.rerun()

    # Per-row editors
    for idx, cf in enumerate(list(st.session_state["custom_fuels"])):
        st.divider()

        # Remove button above the name (as requested)
        _, col_rm = st.columns([1, 1])
        with col_rm:
            if st.button("🗑 Remove", key=f"{cf['id']}_remove", use_container_width=True):
                st.session_state["custom_fuels"].pop(idx)
                if not st.session_state["custom_fuels"]:
                    st.session_state["custom_fuels"].append(_new_custom_fuel())
                st.rerun()

        cf["name"] = st.text_input("Name", value=cf.get("name","Custom fuel"), key=f"{cf['id']}_name")
        cf["qty_t"] = st.number_input("Quantity (t)", min_value=0.0, step=1.0,
                                      value=float(cf.get("qty_t",0.0)), format="%0.0f", key=f"{cf['id']}_qty")
        cf["price_usd"] = st.number_input("Price (USD/t)", min_value=0.0, step=10.0,
                                          value=float(cf.get("price_usd",0.0)), format="%0.0f", key=f"{cf['id']}_price")
        cf["lcv"] = st.number_input("LCV (MJ/g)", min_value=0.0, value=float(cf.get("lcv",0.0400)),
                                    step=0.0001, format="%.4f", key=f"{cf['id']}_lcv")
        cf["rfnbo"] = st.checkbox("RFNBO (x2 energy credit until 2033)", value=bool(cf.get("rfnbo", False)),
                                  key=f"{cf['id']}_rfnbo")

        mode_idx = 0 if str(cf.get("mode","Basic")).startswith("Basic") else 1
        choice = st.radio(
            "Emission input mode",
            ["Basic", "Advanced"],
            index=mode_idx,
            key=f"{cf['id']}_mode",
            help=("Basic: single WtW intensity (counts for FuelEU only, excluded from ETS/splits). "
                  "Advanced: provide WtT & TtW so ETS and splits are computed.")
        )
        cf["mode"] = "Basic" if choice.startswith("Basic") else "Advanced"

        if cf["mode"] == "Basic":
            cf["wtw"] = st.number_input("WtW intensity (gCO₂e/MJ)", min_value=0.0,
                                        value=float(cf.get("wtw", 91.16)), step=0.1, key=f"{cf['id']}_wtw")
        else:
            cf["wtt"] = st.number_input("WtT factor (gCO₂e/MJ)", min_value=0.0,
                                        value=float(cf.get("wtt", 13.2)), step=0.1, key=f"{cf['id']}_wtt")
            cf["ttw_co2"] = st.number_input("TtW CO₂ (g/g fuel)", min_value=0.0,
                                            value=float(cf.get("ttw_co2", 3.114)), step=0.0001, format="%.4f", key=f"{cf['id']}_ttwco2")
            cf["ttw_ch4"] = st.number_input("TtW CH₄ (g/g fuel)", min_value=0.0,
                                            value=float(cf.get("ttw_ch4", 0.0)), step=0.00001, format="%.5f", key=f"{cf['id']}_ttwch4")
            cf["ttw_n2o"] = st.number_input("TtW N₂O (g/g fuel)", min_value=0.0,
                                            value=float(cf.get("ttw_n2o", 0.0)), step=0.00001, format="%.5f", key=f"{cf['id']}_ttwn2o")
            cf["ch4_slip"] = st.number_input("CH₄ slip (g/MJ)", min_value=0.0,
                                             value=float(cf.get("ch4_slip", 0.0)), step=0.1, format="%.1f", key=f"{cf['id']}_slip")

        # Per-row "Add custom fuel" (kept; no top-level Add)
        if st.button("➕ Add custom fuel", key=f"{cf['id']}_add_below", use_container_width=True):
            st.session_state["custom_fuels"].insert(idx + 1, _new_custom_fuel())
            st.rerun()

# Mark whether custom fuels should be used (any with qty > 0)
st.session_state["use_custom_fuels"] = any(float(cf.get("qty_t", 0)) > 0 for cf in st.session_state["custom_fuels"])


# EUA price and FX
st.sidebar.header("EU ETS Pricing")
eua_price = st.sidebar.number_input(
    "EU ETS Allowance Price (EUR/tCO2eq)", min_value=0.0, value=0.0, step=10.0, format="%0.0f",
    help="Enter current market price per tCO2eq for EU ETS allowances (EUA).",)

st.sidebar.markdown("---")
exchange_rate = st.sidebar.number_input(
    "EUR/USD Exchange Rate", min_value=0.000001, value=1.000000, step=0.000001, format="%.6f",
    help="Exchange rate to convert USD fuel prices to EUR (EUR = USD * rate).",)

# Other params
st.sidebar.header("Input Parameters")
year = st.sidebar.selectbox("Compliance Year", [2020, 2025, 2030, 2035, 2040, 2045, 2050], index=1)
gwp_choice = st.sidebar.radio(
    "GWP Standard", ["AR4", "AR5"], index=0,
    help=(
        "Choose Global Warming Potential values: AR4 (CH₄:25, N₂O:298) or AR5 (CH₄:29.8, N₂O:273). "
        "Use AR4 for 2025 per current regulation; AR5 expected before Jan 2026 — better for methane-emitting fuels."),)
gwp = GWP_VALUES[gwp_choice]

ops = st.sidebar.selectbox(
    "OPS Reward Factor (%)", list(range(0, 21)), index=0,
    help="Reward factor: % of electricity delivered via OPS. Max 20%.",)
wind = st.sidebar.selectbox(
    "Wind Reward Factor", [1.00, 0.99, 0.97, 0.95], index=0,
    help="Wind-assisted propulsion reward factor (lower = more assistance).",)

# === ETS CONFIG (Coverage & Phase-in) ===
st.sidebar.header("EU ETS Settings")

ets_mode = st.sidebar.radio(
    "Coverage input mode",
    ["Simple", "Advanced"],
    index=0,
    help=(
    "Simple: set Outside‑EU activity and what share of the remaining is Intra‑EU; "
    "Advanced: set coverage & shares per leg type (Intra/Inbound/Outbound/Outside)."),)

if ets_mode == "Simple":
    outside_pct = st.sidebar.slider(
    "Outside‑EU activity (%)", 0, 100, 0,
    help="Voyages entirely between non‑EU/EEA ports (outside ETS scope).",
    )
    intra_of_remaining_pct = st.sidebar.slider(
    "Intra‑EU share of remaining (%)", 0, 100, 100,
    help=(
    "Of the activity that touches the EU (i.e., not Outside‑EU), the % that is entirely within EU/EEA ports. "
    "The rest is split evenly into inbound and outbound extra‑EU legs."),)
    
    # Derive shares
    share_outside = float(outside_pct)
    remaining = 100.0 - share_outside
    share_intra = remaining * (intra_of_remaining_pct / 100.0)
    share_extra = remaining - share_intra
    share_inbound = share_extra / 2.0
    share_outbound = share_extra / 2.0
    
    # Default regulatory coverages (override in Advanced mode if needed)
    cov_intra, cov_inbound, cov_outbound, cov_outside = 100.0, 50.0, 100.0, 0.0

else:
    st.caption("Set coverage (%) by voyage type and your activity shares to derive an effective ETS coverage.")
    cov_intra = st.sidebar.number_input(
    "Coverage: Intra-EU (%)", 0, 100, 100,
    help="Voyages between two EU/EEA ports (incl. at-berth in EU ports). Fraction of these emissions covered by ETS.",
    )
    cov_inbound = st.sidebar.number_input(
    "Coverage: Inbound to EU (%)", 0, 100, 50,
    help="Legs from the last non‑EU/EEA port to an EU/EEA port. Fraction of these emissions covered by ETS.",
    )
    cov_outbound = st.sidebar.number_input(
    "Coverage: Outbound from EU (%)", 0, 100, 100,
    help="Legs from an EU/EEA port to the first non‑EU/EEA port. Fraction of these emissions covered by ETS.",
    )
    cov_outside = st.sidebar.number_input(
    "Coverage: Outside EU (%)", 0, 100, 0,
    help="Voyages between non‑EU/EEA ports. Fraction covered by ETS (often 0%).",
    )
    st.markdown("**Activity mix (shares should roughly sum to 100%)**")
    share_intra = st.sidebar.number_input(
    "Share: Intra-EU (%)", 0.0, 100.0, 100.0, step=1.0,
    help="Share of your annual activity attributable to Intra‑EU voyages (by energy/fuel/emissions).",
    )
    share_inbound = st.sidebar.number_input(
    "Share: Inbound to EU (%)", 0.0, 100.0, 0.0, step=1.0,
    help="Share of your annual activity on legs arriving from non‑EU/EEA ports to EU/EEA ports.",
    )
    share_outbound = st.sidebar.number_input(
    "Share: Outbound from EU (%)", 0.0, 100.0, 0.0, step=1.0,
    help="Share of your annual activity on legs departing EU/EEA ports to the first non‑EU/EEA port.",
    )
    share_outside = st.sidebar.number_input(
    "Share: Outside EU (%)", 0.0, 100.0, 0.0, step=1.0,
    help="Share of your annual activity on voyages entirely between non‑EU/EEA ports (outside ETS scope).",
    )
    
# Effective coverage from the (possibly derived) shares and coverages
share_sum = max(share_intra + share_inbound + share_outbound + share_outside, 1.0)
effective_coverage_pct = (
(cov_intra * share_intra) + (cov_inbound * share_inbound) + (cov_outbound * share_outbound) + (cov_outside * share_outside)) / share_sum

# Phase-in and non-CO2 rule
auto_phase_default = default_phase_in_pct(year)
phase_in_pct = st.sidebar.slider(
"Phase-in (%)", 0, 100, auto_phase_default,
help="Default follows EU ETS maritime: 2025→70%, 2026+→100%. Override as needed.",
)
st.info(f"Effective ETS coverage: **{effective_coverage_pct:.1f}%** | Phase-in: **{phase_in_pct}%**")
include_nonco2_in_ets = (year >= 2026) # CH4 + N2O + slip from 2026 and after

# === CALCULATIONS ===
getcontext().prec = 28

# Totals
total_energy = Decimal("0")   # MJ
wtt_sum = Decimal("0")        # gCO2eq (WtT)
ttw_co2_sum = Decimal("0")    # gCO2eq (CO2 only)
ttw_nonco2_sum = Decimal("0") # gCO2eq (CH4 + N2O + slip)
emissions = Decimal("0")      # gCO2eq (WtW = WtT + TtW)
rows = []

for fuel in FUELS:
    qty = Decimal(str(fuel_inputs.get(fuel["name"], 0.0)))  # tonnes
    if qty > 0:
        mass_g = qty * Decimal("1000000")  # g
        lcv = Decimal(str(fuel["lcv"]))  # MJ/g
        energy = mass_g * lcv  # MJ
        if fuel["rfnbo"] and year <= 2033:
            energy *= Decimal(str(REWARD_FACTOR_RFNBO_MULTIPLIER))

        # Per-gram TTW factors
        co2_per_g = Decimal(str(fuel["ttw_co2"])) * Decimal(str(1 - ops / 100)) * Decimal(str(wind))
        ch4_per_g = Decimal(str(fuel["ttw_ch4"])) * Decimal(str(gwp["CH4"]))
        n2o_per_g = Decimal(str(fuel["ttw_n2O"])) * Decimal(str(gwp["N2O"]))
        # Slip (g CH4 / MJ) * GWP * energy (MJ)
        slip_total = Decimal(str(fuel.get("ch4_slip", 0.0))) * Decimal(str(gwp["CH4"])) * energy

        # Components
        ttw_co2 = co2_per_g * mass_g
        ttw_nonco2 = (ch4_per_g + n2o_per_g) * mass_g + slip_total
        wtt_total = energy * Decimal(str(fuel["wtt"]))

        ttw_total = ttw_co2 + ttw_nonco2
        total_emissions = ttw_total + wtt_total

        total_energy += energy
        wtt_sum += wtt_total
        ttw_co2_sum += ttw_co2
        ttw_nonco2_sum += ttw_nonco2
        emissions += total_emissions

        ghg_intensity_mj = (total_emissions / energy) if energy > 0 else Decimal("0")

        price_usd = Decimal(str(fuel_price_inputs.get(fuel["name"], 0.0)))
        price_eur = price_usd * Decimal(str(exchange_rate))
        cost = qty * price_eur

        rows.append({
            "Fuel": fuel["name"],
            "Quantity (t)": float(qty),
            "Price per Tonne (USD)": float(price_usd),
            "Cost (Eur)": float(cost),
            "TTW CO2 (g)": float(ttw_co2),
            "TTW non-CO2 (g)": float(ttw_nonco2),
            "WtT (g)": float(wtt_total),
            "Emissions (gCO2eq)": float(total_emissions),  # WtW
            "Energy (MJ)": float(energy),
            "GHG Intensity (gCO2eq/MJ)": float(ghg_intensity_mj),})

# === CUSTOM FUEL CALCULATIONS ===
if st.session_state.get("use_custom_fuels"):
    for cf in st.session_state.get("custom_fuels", []):
        qty_t = Decimal(str(cf.get("qty_t", 0.0)))
        if qty_t <= 0:
            continue

        mass_g = qty_t * Decimal("1000000")
        lcv = Decimal(str(cf.get("lcv", 0.0)))
        energy = mass_g * lcv

        if cf.get("rfnbo") and year <= 2033:
            energy *= Decimal(str(REWARD_FACTOR_RFNBO_MULTIPLIER))

        price_eur = Decimal(str(cf.get("price_usd", 0.0))) * Decimal(str(exchange_rate))
        cost_eur = qty_t * price_eur

        if cf.get("mode") == "Basic":
            # WtW-only; excluded from ETS splits
            wtw = Decimal(str(cf.get("wtw", 0.0)))  # gCO2e/MJ
            total_emissions_cf = energy * wtw

            total_energy += energy
            emissions += total_emissions_cf

            ghg_intensity_mj_cf = (total_emissions_cf / energy) if energy > 0 else Decimal("0")

            rows.append({
                "Fuel": f"{cf.get('name','Custom fuel')} (custom, WtW-only)",
                "Quantity (t)": float(qty_t),
                "Price per Tonne (USD)": float(Decimal(str(cf.get("price_usd", 0.0)))),
                "Cost (Eur)": float(cost_eur),
                "TTW CO2 (g)": float("nan"),
                "TTW non-CO2 (g)": float("nan"),
                "WtT (g)": float("nan"),
                "Emissions (gCO2eq)": float(total_emissions_cf),
                "Energy (MJ)": float(energy),
                "GHG Intensity (gCO2eq/MJ)": float(ghg_intensity_mj_cf),})

        else:
            # Advanced: contributes to ETS, WtT/TtW
            co2_per_g = Decimal(str(cf.get("ttw_co2", 0.0))) * Decimal(str(1 - ops / 100)) * Decimal(str(wind))
            ch4_per_g = Decimal(str(cf.get("ttw_ch4", 0.0))) * Decimal(str(gwp["CH4"]))
            n2o_per_g = Decimal(str(cf.get("ttw_n2o", 0.0))) * Decimal(str(gwp["N2O"]))
            slip_total = Decimal(str(cf.get("ch4_slip", 0.0))) * Decimal(str(gwp["CH4"])) * energy

            ttw_co2_cf = co2_per_g * mass_g
            ttw_nonco2_cf = (ch4_per_g + n2o_per_g) * mass_g + slip_total
            wtt_total_cf = energy * Decimal(str(cf.get("wtt", 0.0)))

            total_emissions_cf = ttw_co2_cf + ttw_nonco2_cf + wtt_total_cf

            total_energy += energy
            wtt_sum += wtt_total_cf
            ttw_co2_sum += ttw_co2_cf
            ttw_nonco2_sum += ttw_nonco2_cf
            emissions += total_emissions_cf

            ghg_intensity_mj_cf = (total_emissions_cf / energy) if energy > 0 else Decimal("0")

            rows.append({
                "Fuel": f"{cf.get('name','Custom fuel')} (custom)",
                "Quantity (t)": float(qty_t),
                "Price per Tonne (USD)": float(Decimal(str(cf.get("price_usd", 0.0)))),
                "Cost (Eur)": float(cost_eur),
                "TTW CO2 (g)": float(ttw_co2_cf),
                "TTW non-CO2 (g)": float(ttw_nonco2_cf),
                "WtT (g)": float(wtt_total_cf),
                "Emissions (gCO2eq)": float(total_emissions_cf),
                "Energy (MJ)": float(energy),
                "GHG Intensity (gCO2eq/MJ)": float(ghg_intensity_mj_cf),})

# Summary totals
emissions_tonnes = float(emissions / Decimal("1000000"))  # WtW

ghg_intensity = float(emissions / total_energy) if total_energy > 0 else 0.0
st.session_state["computed_ghg"] = ghg_intensity

# ETS cost (TtW-only with 2026+ non-CO2 and coverage & phase-in)
ets_cost, ets_covered_tonnes = compute_ets_cost(
    ttw_co2_sum, ttw_nonco2_sum, eua_price, effective_coverage_pct, phase_in_pct, include_nonco2_in_ets)

# Positive = surplus (good), Negative = deficit (bad)
compliance_balance = float(total_energy) * (target_intensity(year) - ghg_intensity) / 1_000_000.0  # tCO2eq

# Penalty only if there is a negative compliance balance (deficit)
if compliance_balance < 0:
    penalty = (abs(compliance_balance) / (ghg_intensity * VLSFO_ENERGY_CONTENT)) * PENALTY_RATE * 1_000_000
else:
    penalty = 0.0

# Mitigation scaffolding
added_biofuel_cost = 0.0
mitigation_rows = []
new_blend_ets_cost = None

# Substitution scaffolding
substitution_price_usd = 0.0
additional_substitution_cost = None
replaced_mass = None
best_x = None
substitution_total_emissions = None
substitution_ets_cost = None
total_substitution_cost = None

# === RESET HANDLER (light) ===
if st.session_state.get("trigger_reset", False):
    exclude_keys = {"exchange_rate"}
    for key in list(st.session_state.keys()):
        if key not in exclude_keys and key != "trigger_reset":
            del st.session_state[key]
    st.session_state["trigger_reset"] = False
    st.experimental_rerun()

# === OUTPUT TABLES & METRICS ===
user_entered_prices = any(r.get("Price per Tonne (USD)", 0) > 0 for r in rows)

if rows:
    header_col, details_col = st.columns([7, 2])
    with header_col:
        st.subheader("Fuel Breakdown")
    with details_col:
        show_details = st.checkbox("🔍 Fuel Details", value=False, key="show_details_inline")

    df_raw = pd.DataFrame(rows).sort_values("Emissions (gCO2eq)", ascending=False).reset_index(drop=True)
    cols = ["Fuel", "Quantity (t)"]
    if user_entered_prices:
        cols += ["Price per Tonne (USD)", "Cost (Eur)"]
    cols += ["TTW CO2 (g)", "TTW non-CO2 (g)", "WtT (g)", "Emissions (gCO2eq)", "Energy (MJ)", "GHG Intensity (gCO2eq/MJ)"]
    df_display = df_raw[cols]

    fmt = {
        "Quantity (t)": "{:,.0f}",
        "TTW CO2 (g)": "{:,.0f}",
        "TTW non-CO2 (g)": "{:,.0f}",
        "WtT (g)": "{:,.0f}",
        "Emissions (gCO2eq)": "{:,.0f}",
        "Energy (MJ)": "{:,.0f}",
        "GHG Intensity (gCO2eq/MJ)": "{:,.2f}",
    }
    if user_entered_prices:
        fmt.update({"Price per Tonne (USD)": "{:,.2f}", "Cost (Eur)": "{:,.2f}"})

    st.dataframe(df_display.style.format(fmt))

    if show_details:
        # Details of selected fuels
        selected = [name for name, qty in fuel_inputs.items() if qty > 0]
        detail_rows = []
        for fuel in FUELS:
            if fuel["name"] in selected:
                row = {
                    "Fuel": fuel["name"],
                    "LCV (MJ/g)": fuel["lcv"],
                    "WtT Factor (gCO2eq/MJ)": fuel["wtt"],
                    "TtW CO2 (g/g)": fuel["ttw_co2"],
                    "TtW CH4 (g/g)": fuel["ttw_ch4"],
                    "TtW N2O (g/g)": fuel["ttw_n2O"],}
                if "ch4_slip" in fuel:
                    row["CH4 Slip (g/MJ)"] = fuel["ch4_slip"]
                detail_rows.append(row)
        if st.session_state.get("use_custom_fuels"):
            for cf in st.session_state.get("custom_fuels", []):
                if cf.get("mode") == "Advanced" and float(cf.get("qty_t", 0)) > 0:
                    row = {
                        "Fuel": f"{cf.get('name','Custom fuel')} (custom)",
                        "LCV (MJ/g)": cf["lcv"],
                        "WtT Factor (gCO2eq/MJ)": cf["wtt"],
                        "TtW CO2 (g/g)": cf["ttw_co2"],
                        "TtW CH4 (g/g)": cf["ttw_ch4"],
                        "TtW N2O (g/g)": cf["ttw_n2o"],}
                    if cf.get("ch4_slip", 0.0):
                        row["CH4 Slip (g/MJ)"] = cf["ch4_slip"]
                    detail_rows.append(row)
        if detail_rows:
            st.subheader("LCV & Emission Factors")
            st.dataframe(pd.DataFrame(detail_rows).style.format({
                "LCV (MJ/g)": "{:.4f}",
                "WtT Factor (gCO2eq/MJ)": "{:.2f}",
                "TtW CO2 (g/g)": "{:.3f}",
                "TtW CH4 (g/g)": "{:.5f}",
                "TtW N2O (g/g)": "{:.5f}",
                "CH4 Slip (g/MJ)": "{:.1f}",}))

    total_cost = sum(row["Cost (Eur)"] for row in rows)
    if user_entered_prices:
        st.metric("Total Fuel Cost (Eur)", f"{total_cost:,.2f}")

    # Summary (WtW & ETS TtW)
    st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.2f}")
    st.metric("Total Emissions (WtW, tCO2eq)", f"{emissions_tonnes:,.2f}")
    st.metric("ETS-eligible TtW (covered, tCO2eq)", f"{ets_covered_tonnes:,.2f}")
    if eua_price > 0.0:
        st.metric("EU ETS Cost (EUR)", f"{ets_cost:,.2f}")
    st.metric("Compliance Balance (tCO2eq)", f"{compliance_balance:,.2f}")
    st.metric("Estimated Penalty (EUR)", f"{penalty:,.2f}")

    # Always define conservative_total for later use
    conservative_total = (total_cost if user_entered_prices else 0.0) + (penalty or 0.0) + (ets_cost if eua_price > 0 else 0.0)

    # Display rolled-up totals
    if user_entered_prices:
        label = "Total Cost of Selected Fuels (Eur)"
        if penalty > 0 and eua_price > 0:
            label = "Total Cost + Penalty + EU ETS (Eur)"
        elif penalty > 0:
            label = "Total Cost + Penalty (Eur)"
        elif eua_price > 0:
            label = "Total Cost + EU ETS (Eur)"
        st.metric(label, f"{conservative_total:,.2f}")

    # === MITIGATION STRATEGIES ===
    if compliance_balance < 0:
        st.subheader("Mitigation Strategies")

        # --- POOLING OPTION ---
        with st.expander("**Pooling**", expanded=False):
            st.info(f"CO2 Deficit: {abs(compliance_balance):,.0f} tCO2eq. Offset via pooling if you have access to external credits.")
            pooling_price_usd_per_tonne = st.number_input(
                "Pooling Price (USD/tCO2eq)", min_value=0.0, value=100.0, step=10.0, format="%0.0f",
                help="Cost per tCO2eq to buy compliance credits. If 0, pooling is ignored.",
            )
            pooling_cost_eur = pooling_price_usd_per_tonne * exchange_rate * abs(compliance_balance) if pooling_price_usd_per_tonne > 0 else 0.0
            total_with_pooling = (total_cost if user_entered_prices else 0.0) + pooling_cost_eur + (ets_cost if eua_price > 0 else 0.0)
            if pooling_price_usd_per_tonne > 0:
                st.metric("Pooling Cost (Eur)", f"{pooling_cost_eur:,.2f}")

        # --- ADD BIO FUEL (ADDITION) ---
        with st.expander("**Add Bio Fuel**", expanded=False):
            st.info("Adds mitigation fuel on top of current fuels (total energy increases).")
            dec_ghg = Decimal(str(ghg_intensity))
            dec_emissions = Decimal(str(emissions))
            dec_energy = Decimal(str(total_energy))
            dec_ttw_co2_sum = Decimal(str(ttw_co2_sum))
            dec_ttw_nonco2_sum = Decimal(str(ttw_nonco2_sum))
            target = Decimal(str(target_intensity(year)))

            mitigation_rows = []
            for fuel in FUELS:
                # Compute per-unit intensities
                co2_g = Decimal(str(fuel["ttw_co2"])) * Decimal(str(1 - ops / 100)) * Decimal(str(wind))
                ch4_g = Decimal(str(fuel["ttw_ch4"])) * Decimal(str(gwp["CH4"]))
                n2o_g = Decimal(str(fuel["ttw_n2O"])) * Decimal(str(gwp["N2O"]))
                wtt_mj = Decimal(str(fuel["wtt"]))
                slip_mj = Decimal(str(fuel.get("ch4_slip", 0.0))) * Decimal(str(gwp["CH4"]))
                approx_intensity = wtt_mj + (co2_g + ch4_g + n2o_g) * Decimal(str(fuel["lcv"])) + slip_mj
                if approx_intensity >= dec_ghg:
                    continue

                low = Decimal("0")
                high = Decimal("100000.0")
                best_qty = None
                for _ in range(50):
                    mid = (low + high) / 2
                    mass_g = mid * Decimal("1000000")
                    energy_mj = mass_g * Decimal(str(fuel["lcv"]))
                    if fuel["rfnbo"] and year <= 2033:
                        energy_mj *= Decimal(str(REWARD_FACTOR_RFNBO_MULTIPLIER))
                    ttw_co2_add = co2_g * mass_g
                    ttw_nonco2_add = (ch4_g + n2o_g) * mass_g + slip_mj * energy_mj
                    ttw_add = ttw_co2_add + ttw_nonco2_add
                    wtt_add = wtt_mj * energy_mj

                    new_emissions = dec_emissions + ttw_add + wtt_add
                    new_energy = dec_energy + energy_mj
                    new_ghg = new_emissions / new_energy if new_energy > 0 else Decimal("1e9")
                    if new_ghg <= target:
                        best_qty = mid
                        high = mid
                    else:
                        low = mid
                    if high - low < Decimal("0.00001"):
                        break

                if best_qty is not None:
                    mass_g = best_qty * Decimal("1000000")
                    energy_mj = mass_g * Decimal(str(fuel["lcv"]))
                    if fuel["rfnbo"] and year <= 2033:
                        energy_mj *= Decimal(str(REWARD_FACTOR_RFNBO_MULTIPLIER))
                    ttw_co2_add = co2_g * mass_g
                    ttw_nonco2_add = (ch4_g + n2o_g) * mass_g + slip_mj * energy_mj
                    wtt_add = wtt_mj * energy_mj
                    new_emissions = dec_emissions + (ttw_co2_add + ttw_nonco2_add) + wtt_add

                    # ETS for the new blend
                    new_ttw_co2_total = dec_ttw_co2_sum + ttw_co2_add
                    new_ttw_nonco2_total = dec_ttw_nonco2_sum + ttw_nonco2_add
                    new_blend_ets_cost, _ = compute_ets_cost(
                        new_ttw_co2_total, new_ttw_nonco2_total, eua_price, effective_coverage_pct, phase_in_pct, include_nonco2_in_ets)

                    mitigation_rows.append({
                        "Fuel": fuel["name"],
                        "Required Amount (t)": float(math.ceil(float(best_qty))),
                        "New Emissions (gCO2eq)": float(new_emissions),
                        "ETS Cost (EUR)": float(new_blend_ets_cost),})

            if mitigation_rows:
                mitigation_rows = sorted(mitigation_rows, key=lambda x: x["Required Amount (t)"])
                df_mit = pd.DataFrame(mitigation_rows)
                st.dataframe(df_mit.style.format({
                    "Required Amount (t)": "{:,.0f}",
                    "New Emissions (gCO2eq)": "{:,.0f}",
                    "ETS Cost (EUR)": "{:,.2f}",}))

                # Optional: price input for a single chosen mitigation fuel
                default_fuel = "Biodiesel (UCO,B24)"
                fuel_names = [row["Fuel"] for row in mitigation_rows]
                default_index = fuel_names.index(default_fuel) if default_fuel in fuel_names else 0
                selected_fuel = st.selectbox("Select Mitigation Fuel for Pricing", fuel_names, index=default_index)
                mitigation_price_usd = st.number_input(
                    f"{selected_fuel} - Price (USD/t)", min_value=0.0, value=0.0, step=10.0, key=f"mitigation_price_input_{selected_fuel.replace(' ', '_')}"
                )
                # capture ETS cost for the selected blend
                selected_row = next((row for row in mitigation_rows if row["Fuel"] == selected_fuel), None)
                if selected_row is not None:
                    new_blend_ets_cost = selected_row.get("ETS Cost (EUR)")
                if mitigation_price_usd > 0:
                    for row in mitigation_rows:
                        row["Price (USD/t)"] = mitigation_price_usd if row["Fuel"] == selected_fuel else 0.0
                        row["Estimated Cost (Eur)"] = row.get("Price (USD/t)", 0.0) * exchange_rate * row["Required Amount (t)"]
                    added_biofuel_cost = sum(row.get("Estimated Cost (Eur)", 0.0) for row in mitigation_rows)
                    st.markdown(f"**Bio Fuel Cost:** {added_biofuel_cost:,.2f} EUR")
                    if eua_price > 0:
                        st.markdown(f"**EU ETS Cost:** {new_blend_ets_cost:,.2f} EUR")

        # --- SUBSTITUTION (REPLACEMENT) ---
        with st.expander("**Replace high-emission fuel with Bio/RFNBO**", expanded=False):
            st.info("Replaces a fraction of a selected fossil fuel with a mitigation fuel; total energy remains close to original for that stream.")
            initial_fuel = st.selectbox("Fuel to replace", initial_fuels, key="sub_initial")
            substitute_fuel = st.selectbox("Mitigation fuel", alternative_fuels, index=(alternative_fuels.index("Biodiesel (UCO,B24)") if "Biodiesel (UCO,B24)" in alternative_fuels else 0), key="sub_mitigation")
            qty_initial = float(fuel_inputs.get(initial_fuel, 0.0))  # t
            price_initial_eur_per_t = float(fuel_price_inputs.get(initial_fuel, 0.0)) * float(exchange_rate)
            substitution_price_usd = st.number_input(
                f"{substitute_fuel} - Price (USD/t)", min_value=0.0, value=0.0, step=10.0, key="substitution_price_input"
            )
            substitution_price_eur_per_t = substitution_price_usd * exchange_rate

            if qty_initial > 0:
                # Pull props
                fi = next(f for f in FUELS if f["name"] == initial_fuel)
                fm = next(f for f in FUELS if f["name"] == substitute_fuel)

                # Precompute per-gram and per-MJ bits
                co2_i = fi["ttw_co2"] * (1 - ops / 100) * wind
                ch4_i = fi["ttw_ch4"] * gwp["CH4"]
                n2o_i = fi["ttw_n2O"] * gwp["N2O"]
                slip_i = fi.get("ch4_slip", 0.0) * gwp["CH4"]  # per MJ

                co2_m = fm["ttw_co2"] * (1 - ops / 100) * wind
                ch4_m = fm["ttw_ch4"] * gwp["CH4"]
                n2o_m = fm["ttw_n2O"] * gwp["N2O"]
                slip_m = fm.get("ch4_slip", 0.0) * gwp["CH4"]  # per MJ

                lcv_i = fi["lcv"]; lcv_m = fm["lcv"]
                wtt_i = fi["wtt"];  wtt_m = fm["wtt"]

                target_val = target_intensity(year)
                precision = 1e-6
                low, high = 0.0, 1.0
                best_x = None

                total_energy_all = float(total_energy)
                # Original initial stream components (for removal)
                initial_mass_g = qty_initial * 1_000_000.0
                initial_energy_stream = initial_mass_g * lcv_i
                initial_ttw_co2_stream = initial_mass_g * co2_i
                initial_ttw_nonco2_stream = initial_mass_g * (ch4_i + n2o_i) + initial_energy_stream * slip_i
                initial_wtt_stream = initial_energy_stream * wtt_i
                initial_total_stream = initial_ttw_co2_stream + initial_ttw_nonco2_stream + initial_wtt_stream

                # Base totals in float for reuse
                base_ttw_co2 = float(ttw_co2_sum)
                base_ttw_nonco2 = float(ttw_nonco2_sum)
                base_wtt = float(wtt_sum)
                base_wtw = base_ttw_co2 + base_ttw_nonco2 + base_wtt

                for _ in range(100):
                    mid = (low + high) / 2
                    sub_mass_g = initial_mass_g * mid
                    remain_mass_g = initial_mass_g * (1 - mid)

                    energy_initial_part = remain_mass_g * lcv_i
                    energy_sub_part = sub_mass_g * lcv_m
                    if fm["rfnbo"] and year <= 2033:
                        energy_sub_part *= REWARD_FACTOR_RFNBO_MULTIPLIER

                    # TTW components for parts
                    ttw_i_co2_part = remain_mass_g * co2_i
                    ttw_i_nonco2_part = remain_mass_g * (ch4_i + n2o_i) + energy_initial_part * slip_i
                    ttw_m_co2_part = sub_mass_g * co2_m
                    ttw_m_nonco2_part = sub_mass_g * (ch4_m + n2o_m) + energy_sub_part * slip_m

                    wtt_i_part = energy_initial_part * wtt_i
                    wtt_m_part = energy_sub_part * wtt_m

                    # Replace initial stream with parts in totals
                    total_energy_blend = total_energy_all - initial_energy_stream + (energy_initial_part + energy_sub_part)
                    ttw_co2_blend = base_ttw_co2 - initial_ttw_co2_stream + (ttw_i_co2_part + ttw_m_co2_part)
                    ttw_nonco2_blend = base_ttw_nonco2 - initial_ttw_nonco2_stream + (ttw_i_nonco2_part + ttw_m_nonco2_part)
                    wtt_blend = base_wtt - initial_wtt_stream + (wtt_i_part + wtt_m_part)
                    total_emissions_blend = ttw_co2_blend + ttw_nonco2_blend + wtt_blend

                    blended_ghg = total_emissions_blend / total_energy_blend if total_energy_blend > 0 else 1e9
                    if blended_ghg <= target_val + precision:
                        best_x = mid
                        high = mid
                    else:
                        low = mid
                    if (high - low) < precision:
                        break

                if best_x is None or best_x > 1.0:
                    st.warning("⚠️ No feasible replacement fraction found. Consider another mitigation fuel.")
                else:
                    replaced_mass = best_x * qty_initial  # tonnes
                    # Recompute emissions for best_x for reporting
                    sub_mass_g = initial_mass_g * best_x
                    remain_mass_g = initial_mass_g * (1 - best_x)
                    energy_initial_part = remain_mass_g * lcv_i
                    energy_sub_part = sub_mass_g * lcv_m
                    if fm["rfnbo"] and year <= 2033:
                        energy_sub_part *= REWARD_FACTOR_RFNBO_MULTIPLIER

                    ttw_i_co2_part = remain_mass_g * co2_i
                    ttw_i_nonco2_part = remain_mass_g * (ch4_i + n2o_i) + energy_initial_part * slip_i
                    ttw_m_co2_part = sub_mass_g * co2_m
                    ttw_m_nonco2_part = sub_mass_g * (ch4_m + n2o_m) + energy_sub_part * slip_m

                    wtt_i_part = energy_initial_part * wtt_i
                    wtt_m_part = energy_sub_part * wtt_m

                    total_energy_blend = total_energy_all - initial_energy_stream + (energy_initial_part + energy_sub_part)
                    ttw_co2_blend = base_ttw_co2 - initial_ttw_co2_stream + (ttw_i_co2_part + ttw_m_co2_part)
                    ttw_nonco2_blend = base_ttw_nonco2 - initial_ttw_nonco2_stream + (ttw_i_nonco2_part + ttw_m_nonco2_part)
                    wtt_blend = base_wtt - initial_wtt_stream + (wtt_i_part + wtt_m_part)
                    substitution_total_emissions = ttw_co2_blend + ttw_nonco2_blend + wtt_blend

                    # ETS for substitution blend
                    substitution_ets_cost, _ = compute_ets_cost(
                        Decimal(str(ttw_co2_blend)), Decimal(str(ttw_nonco2_blend)), eua_price,
                        effective_coverage_pct, phase_in_pct, include_nonco2_in_ets
                    )

                    st.success(
                        f"To reach {target_val:.2f} gCO2eq/MJ, replace **{best_x*100:.2f}%** of {initial_fuel} with {substitute_fuel}."
                    )
                    st.markdown(f"**Replaced {initial_fuel} mass**: {replaced_mass:,.2f} t")
                    st.markdown(f"**Added {substitute_fuel} mass**: {replaced_mass:,.2f} t")

                    if user_entered_prices and substitution_price_usd > 0:
                        mitigation_fuel_cost = replaced_mass * substitution_price_eur_per_t
                        remaining_fuel_cost = (qty_initial - replaced_mass) * price_initial_eur_per_t
                        additional_substitution_cost = replaced_mass * (substitution_price_eur_per_t - price_initial_eur_per_t)
                        substitution_total_cost_stream = mitigation_fuel_cost + remaining_fuel_cost
                        other_fuel_costs = sum(
                            (fuel_inputs.get(f["name"], 0.0) * fuel_price_inputs.get(f["name"], 0.0) * exchange_rate)
                            for f in FUELS if f["name"] != initial_fuel
                        )
                        total_substitution_cost = substitution_total_cost_stream + other_fuel_costs + (substitution_ets_cost or 0.0)

                    if additional_substitution_cost is not None:
                        st.markdown(f"**Additional fuel cost**: {additional_substitution_cost:,.2f} EUR")
                    if eua_price > 0:
                        st.markdown(f"**EU ETS Cost**: {substitution_ets_cost:,.2f} EUR")

        # --- COST-BENEFIT ANALYSIS ---
        if user_entered_prices:
            st.subheader("Cost-Benefit Analysis")
            st.metric(
                "Initial fuels" + (" + Penalty" if penalty > 0 else "") + (" + EU ETS" if eua_price > 0 else ""), f"{(conservative_total):,.2f}")
            
            # Pooling Option
            if pooling_price_usd_per_tonne and eua_price > 0:    
                st.metric("Initial fuels + Pooling" + (" + EU ETS" if eua_price > 0 else "") + " (No Penalty)", f"{total_with_pooling:,.2f}")

            # Bio fuel addition (if priced)
            if added_biofuel_cost > 0:
                ets_component = (
                    new_blend_ets_cost if (eua_price > 0 and new_blend_ets_cost is not None)
                    else (ets_cost if eua_price > 0 else 0.0))
                st.metric(
                    "Initial fuels + Bio Fuels" + (" + EU ETS" if eua_price > 0 else "") + " (No Penalty)",f"{(total_cost + added_biofuel_cost + ets_component):,.2f}")
                
            # Substitution
            if substitution_price_usd > 0 and total_substitution_cost is not None:
                st.metric(
                    "Fuel Replacement" + (" + EU ETS" if eua_price > 0 else "") + " (No Penalty)",f"{total_substitution_cost:,.2f}")
    else:
        st.info("✅ Compliance already achieved! No mitigation strategy required.")
else:
    st.info("No fuel data provided yet.")

# === COMPLIANCE CHART ===
years = sorted(set([2025] + list(REDUCTIONS.keys())))
def _sector_target_for_plot(y: int) -> float:
# FuelEU applies from 2025; show baseline (no reduction) for 2024
    return BASE_TARGET if y < 2025 else BASE_TARGET * (1 - REDUCTIONS[y])
targets = [_sector_target_for_plot(y) for y in years]

st.subheader("Sector-wide GHG Intensity Targets")
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(years, targets, linestyle='--', marker='o', label='EU Target')
for x, yv in zip(years, targets):
    ax.annotate(f"{yv:.2f}", (x, yv), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)
computed_ghg = st.session_state.get("computed_ghg", ghg_intensity)
line_color = 'red' if computed_ghg > target_intensity(year) else 'green'
ax.axhline(computed_ghg, color=line_color, linestyle='-', label='Your GHG Intensity')
ax.annotate(f"{computed_ghg:.2f}", xy=(max(years), computed_ghg), xytext=(0, -10), textcoords="offset points", ha="center", va="top", fontsize=10)
ax.set_xlabel(None)
ax.set_ylabel("gCO2eq/MJ")
ax.set_title("Your Performance vs Sector Target")
ax.legend()
ax.grid(True)
st.pyplot(fig)


# === REGULATORY DYNAMICS (STACKED COLUMNS) ===
st.subheader("Regulatory Dynamics: FuelEU vs EU ETS")

# Milestone years for display (include ETS start & FuelEU targets)
years_dyn = sorted(set([2025, 2026] + list(REDUCTIONS.keys())))

# FuelEU: reduction vs baseline as % and remaining intensity %
fueleu_reduction_pct = [max(0.0, min(100.0, (BASE_TARGET - target_intensity(y)) / BASE_TARGET * 100.0)) for y in years_dyn]
fueleu_remaining_pct = [100.0 - r for r in fueleu_reduction_pct]

# ETS: effective coverage path = coverage * phase-in (policy schedule)
def _ets_phase(y: int) -> int:
    if y <= 2023:
        return 0
    if y == 2024:
        return 40
    if y == 2025:
        return 70
    return 100 # 2026+

ets_effective_pct = [float(effective_coverage_pct) * _ets_phase(y) / 100.0 for y in years_dyn]
ets_uncovered_pct = [max(0.0, 100.0 - c) for c in ets_effective_pct]

x = np.arange(len(years_dyn))
width = 0.38

fig_dyn, ax_dyn = plt.subplots(figsize=(10, 4))

# ETS stacked (covered vs uncovered)
ax_dyn.bar(x - width/2, ets_effective_pct, width, label='ETS covered (%)')
ax_dyn.bar(x - width/2, ets_uncovered_pct, width, bottom=ets_effective_pct, label='ETS not covered (%)')

# FuelEU stacked (required reduction vs remaining intensity)
ax_dyn.bar(x + width/2, fueleu_reduction_pct, width, label='FuelEU required reduction (%)')
ax_dyn.bar(x + width/2, fueleu_remaining_pct, width, bottom=fueleu_reduction_pct, label='Remaining intensity (%)')

ax_dyn.set_xticks(x)
ax_dyn.set_xticklabels([str(y) for y in years_dyn])
ax_dyn.set_ylabel('%')
ax_dyn.set_title('EU ETS coverage vs FuelEU sector target path')
ax_dyn.legend(ncol=2, loc='upper center')
ax_dyn.grid(axis='y', linestyle='--', alpha=0.5)

# Marker: non-CO₂ enters ETS from 2026
if 2026 in years_dyn:
    idx_2026 = years_dyn.index(2026)
    ax_dyn.axvline(idx_2026, linestyle=':', linewidth=1)
    ylim = ax_dyn.get_ylim()
    ax_dyn.text(idx_2026 + 0.03, ylim[1]*0.95, 'ETS adds CH₄+N₂O from 2026', rotation=90, va='top')

st.pyplot(fig_dyn)

# === PDF EXPORT ===
st.subheader("Export to PDF")

with st.expander("PDF sections to include", expanded=False):
    opt_summary = st.checkbox("Summary header", True)
    opt_ets = st.checkbox("ETS parameters & total", False)
    opt_fuel_table = st.checkbox("Fuel breakdown", True)
    opt_fuel_details_pdf = st.checkbox("Fuel details table (LCV & factors)", False)
    opt_split_totals = st.checkbox("Emissions totals (TtW vs WtT)", False)
    opt_mitigation = st.checkbox("Mitigation overview (if deficit)", True)
    opt_cost_benefit = st.checkbox("Cost–Benefit analysis rollup", True)
    opt_line_chart = st.checkbox("Add line chart: targets", False)
    opt_stack_chart = st.checkbox("Add stacked chart: FuelEU vs ETS", False)

if st.button("Export to PDF (with selections)"):
    if not rows:
        st.warning("No data to export.")
    else:
        pdf = FPDF()
        pdf.add_page()

        # --- Summary header ---
        if opt_summary:
            pdf.set_font("Arial", style="BU", size=12)
            pdf.cell(200, 10, txt="Fuel EU Maritime GHG & Penalty Report", ln=True, align="C")
            pdf.set_font("Arial", "B", size=11)
            pdf.cell(200, 10, txt=f"Year: {year} | GWP: {gwp_choice}", ln=True)
            pdf.cell(200, 10, txt=f"EU Target for {year}: {target_intensity(year):.2f} gCO2eq/MJ", ln=True)
            pdf.cell(200, 10, txt=f"GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ", ln=True)
            pdf.cell(200, 10, txt=f"Compliance Balance: {compliance_balance:,.0f} tCO2eq", ln=True)
            pdf.cell(200, 10, txt=f"Penalty: {penalty:,.0f} Eur", ln=True)
        
        # --- ETS parameters & total ---
        if opt_ets:
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"ETS Coverage (effective): {effective_coverage_pct:.1f}%", ln=True)
            pdf.cell(200, 10, txt=f"ETS Phase-in: {phase_in_pct}%", ln=True)
            pdf.cell(200, 10, txt=f"ETS includes CH4/N2O/slip: {'Yes' if include_nonco2_in_ets else 'No (CO2-only)'}", ln=True)
            if eua_price > 0:
                pdf.cell(200, 10, txt=f"ETS-eligible TtW (covered): {ets_covered_tonnes:,.0f} tCO2eq", ln=True)
                pdf.cell(200, 10, txt=f"EU ETS Cost: {ets_cost:,.0f} Eur", ln=True)

        
        # --- Emissions totals (WtT vs TtW) ---
        if opt_split_totals:
            ttw_total_tonnes = float((ttw_co2_sum + ttw_nonco2_sum) / Decimal("1000000"))
            wtt_total_tonnes = float(wtt_sum / Decimal("1000000"))
            pdf.cell(200, 10, txt=f"TtW Total: {ttw_total_tonnes:,.0f} tCO2eq (CO2: {float(ttw_co2_sum/Decimal('1000000')):,.0f} | non-CO2: {float(ttw_nonco2_sum/Decimal('1000000')):,.0f})", ln=True)
            pdf.cell(200, 10, txt=f"WtT Total: {wtt_total_tonnes:,.0f} tCO2eq", ln=True)
            pdf.cell(200, 10, txt=f"Total Emissions (WtW): {emissions_tonnes:,.0f} tCO2eq", ln=True)
            pdf.ln(5)
        
       # --- Fuel Breakdown ---
        if opt_fuel_table:
            pdf.set_font("Arial", "U", size=10)
            pdf.cell(200, 8, txt="Fuel Breakdown:", ln=True)
            pdf.set_font("Arial", size=10)
        
        if user_entered_prices:
            for row in rows:
                fuel_name = row["Fuel"]
                qty = row["Quantity (t)"]
                price_usd = (row.get("Price per Tonne (USD)") or 0.0)
                cost_eur = (row.get("Cost (Eur)") or 0.0)
                ghg_i = row["GHG Intensity (gCO2eq/MJ)"]
                line = (f"{fuel_name}: {qty:,.0f} t @ {price_usd:,.2f} USD/t | "
                        f"{cost_eur:,.2f} Eur | GHG Intensity: {ghg_i:.2f} gCO2eq/MJ")
                pdf.multi_cell(200, 6, txt=line)
            pdf.ln(2)
            pdf.set_font("Arial", size=8)
            pdf.cell(200, 6, txt=f"Conversion Rate Used: 1 USD = {exchange_rate:.6f} Eur", ln=True)
            pdf.set_font("Arial", "B", size=11)
            rollup = ((total_cost if user_entered_prices else 0.0)
                      + (penalty or 0.0)
                      + (ets_cost if eua_price > 0 else 0.0))
            pdf.cell(200, 8, txt=f"Total Cost: {rollup:,.2f} Eur", ln=True)
        else:
            for row in rows:
                fuel_name = row["Fuel"]
                qty = row["Quantity (t)"]
                ghg_i = row["GHG Intensity (gCO2eq/MJ)"]
                pdf.cell(200, 6, txt=f"{fuel_name}: {qty:,.0f} t | GHG Intensity: {ghg_i:.2f} gCO2eq/MJ", ln=True)

        # --- Fuel Details (LCV & emission factors) ---
        if opt_fuel_details_pdf:
            pdf.ln(3)
            pdf.set_font("Arial", "U", 10)
            pdf.cell(200, 8, "Fuel Details (LCV & Emission Factors):", ln=True)
            pdf.set_font("Arial", size=9)
        
            # Selected stock fuels (qty > 0)
            selected = [name for name, qty in fuel_inputs.items() if qty > 0]
            for f in FUELS:
                if f["name"] not in selected:
                    continue
                line = (f"{f['name']} | LCV {f['lcv']:.4f} MJ/g | WtT {f['wtt']:.2f} g/MJ | "
                        f"TtW CO2 {f['ttw_co2']:.3f} g/g | CH4 {f['ttw_ch4']:.5f} g/g | "
                        f"N2O {f['ttw_n2O']:.5f} g/g")
                if f.get("ch4_slip"):
                    line += f" | CH4 slip {float(f['ch4_slip']):.1f} g/MJ"
                pdf.multi_cell(200, 5, line)
        
            # Custom fuels (qty > 0)
            for cf in st.session_state.get("custom_fuels", []):
                if float(cf.get("qty_t", 0)) <= 0:
                    continue
                is_basic = str(cf.get("mode", "Basic")).startswith("Basic")
                if is_basic:
                    line = (f"{cf.get('name','Custom fuel')} (custom; WtW-only) | "
                            f"LCV {float(cf.get('lcv',0.0)):.4f} MJ/g | "
                            f"WtW {float(cf.get('wtw',0.0)):.2f} g/MJ")
                else:
                    line = (f"{cf.get('name','Custom fuel')} (custom) | "
                            f"LCV {float(cf.get('lcv',0.0)):.4f} MJ/g | "
                            f"WtT {float(cf.get('wtt',0.0)):.2f} g/MJ | "
                            f"TtW CO2 {float(cf.get('ttw_co2',0.0)):.3f} g/g | "
                            f"CH4 {float(cf.get('ttw_ch4',0.0)):.5f} g/g | "
                            f"N2O {float(cf.get('ttw_n2o',0.0)):.5f} g/g")
                    slip = float(cf.get("ch4_slip", 0.0))
                    if slip:
                        line += f" | CH4 slip {slip:.1f} g/MJ"
                pdf.multi_cell(200, 5, line)
        
            pdf.set_font("Arial", size=8)
            pdf.multi_cell(200, 5,
                "Note: Custom fuels entered in Basic mode are excluded from ETS and the split totals (TtW/WtT).")
        
        # --- Mitigation overview (only if deficit) ---
        if opt_mitigation and (compliance_balance < 0):
            pdf.ln(5)
            pdf.set_font("Arial", style="BU", size=10)
            pdf.cell(200, 10, txt="Mitigation Overview", ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt=f"CO2 Deficit to Offset: {abs(compliance_balance):,.0f} tCO2eq", ln=True)
        
        # --- Cost-Benefit Analysis (optional) ---
        if opt_cost_benefit and user_entered_prices:
            # small helper to print a bullet with a breakdown line
            def _pdf_bullet(p, title, total_value, parts):
                """
                parts: list of (label, value) pairs. Zero/None values are skipped.
                """
                p.set_font("Arial", "B", 11)
                p.cell(200, 8, txt=f"- {title}: {total_value:,.2f} Eur", ln=True)
                shown = [(k, v) for (k, v) in parts if (v is not None and float(v) != 0.0)]
                if shown:
                    p.set_font("Arial", "", 10)
                    pieces = " + ".join([f"{k}: {float(v):,.2f}" for k, v in shown])
                    p.multi_cell(200, 6, txt=f"    = {pieces}", align="L")

            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(200, 10, txt="--- Cost-Benefit Analysis ---", ln=True)
        
            # Base scenario
            base_parts = [("Initial fuels", total_cost)]
            label_bits = ["Initial fuels"]
            base_total = total_cost
            if penalty and penalty > 0:
                base_parts.append(("Penalty", penalty))
                label_bits.append("Penalty")
                base_total += penalty
            if eua_price > 0:
                base_parts.append(("EU ETS", ets_cost))
                label_bits.append("EU ETS")
                base_total += ets_cost
            _pdf_bullet(pdf, " + ".join(label_bits), base_total, base_parts)
            
            
            # Pooling (only if a price was entered during the session)
            try:
                _pool_price = float(pooling_price_usd_per_tonne)
            except Exception:
                _pool_price = 0.0
            if _pool_price > 0:
                _pool_cost_eur = _pool_price * float(exchange_rate) * abs(float(compliance_balance))
                pool_parts = [("Initial fuels", total_cost), ("Pooling", _pool_cost_eur)]
                pool_label = "Initial fuels + Pooling"
                pool_total = total_cost + _pool_cost_eur
                if eua_price > 0:
                    pool_parts.append(("EU ETS", ets_cost))
                    pool_label += " + EU ETS"
                    pool_total += ets_cost
                _pdf_bullet(pdf, pool_label + " (no Penalty)", pool_total, pool_parts)
            
            # Bio fuel addition (if priced)
            if added_biofuel_cost > 0:
                ets_component = (
                new_blend_ets_cost if (eua_price > 0 and new_blend_ets_cost is not None)
                else (ets_cost if eua_price > 0 else 0.0))
                bio_parts = [("Initial fuels", total_cost), ("Bio fuels", added_biofuel_cost)]
                bio_label = "Initial fuels + Bio fuels"
                bio_total = total_cost + added_biofuel_cost
                if eua_price > 0:
                    bio_parts.append(("EU ETS", ets_component))
                    bio_label += " + EU ETS"
                    bio_total += ets_component
                _pdf_bullet(pdf, bio_label + " (no Penalty)", bio_total, bio_parts)
            
            # Replacement (if priced)
            try:
                _sub_price = float(substitution_price_usd)
            except Exception:
                _sub_price = 0.0
        
            if _sub_price > 0 and (additional_substitution_cost is not None):
                repl_total_direct = (
                    float(total_cost)
                    + float(additional_substitution_cost)
                    + (float(substitution_ets_cost) if (eua_price > 0 and substitution_ets_cost is not None) else 0.0))
        
                _pdf_bullet(
                    pdf,
                    "Fuel Replacement" + (" + EU ETS, no Penalty" if eua_price > 0 else ", no Penalty"),
                    repl_total_direct,
                    [
                        ("Initial fuels", total_cost),
                        ("Additional fuel cost", additional_substitution_cost),
                        ("EU ETS", substitution_ets_cost if eua_price > 0 else 0.0),],)
            
        
        # --- Optional charts (saved as images and embedded) ---
        chart_tmp_files = []
        try:
            CHART_GAP_MM = 30
            chart_blocks = []
            
            if opt_line_chart and 'fig' in globals():
                tmp_png1 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                fig.savefig(tmp_png1.name, dpi=200, bbox_inches="tight")
                chart_tmp_files.append(tmp_png1.name)
                w_in, h_in = fig.get_size_inches()
                chart_blocks.append(("Sector-wide GHG Intensity Targets", tmp_png1.name, (w_in, h_in)))
        
            if opt_stack_chart and 'fig_dyn' in globals():
                tmp_png2 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                fig_dyn.savefig(tmp_png2.name, dpi=200, bbox_inches="tight")
                chart_tmp_files.append(tmp_png2.name)
                w_in2, h_in2 = fig_dyn.get_size_inches()
                chart_blocks.append(("Regulatory Dynamics: FuelEU vs EU ETS", tmp_png2.name, (w_in2, h_in2)))

            if chart_blocks:
                # Start a single page for charts
                pdf.add_page()
                content_w = pdf.w - pdf.l_margin - pdf.r_margin  # printable width
        
                for title, path, (w_in, h_in) in chart_blocks:
                    # Estimate needed height: title + image + small gap
                    title_h = 6
                    img_h_mm = content_w * (h_in / w_in)  # preserve aspect ratio
                    needed_h = title_h + img_h_mm + 5
                    remaining_h = pdf.h - pdf.b_margin - pdf.get_y()
        
                    if needed_h > remaining_h:
                        pdf.add_page()
        
                    pdf.set_font("Arial", "B", 11)
                    pdf.cell(0, title_h, txt=title, ln=True)
        
                    y_img = pdf.get_y()
                    pdf.image(path, x=pdf.l_margin, y=y_img, w=content_w)
                    pdf.set_y(y_img + img_h_mm + CHART_GAP_MM)  # spacing below image
        except Exception:
            # If chart export fails for any reason, keep going with text-only PDF
            pass
        
        # --- Export file ---
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            tmp_pdf_path = tmp_pdf.name
        
        st.success(f"PDF exported: {os.path.basename(tmp_pdf_path)}")
        with open(tmp_pdf_path, "rb") as f:
            st.download_button("Download PDF", data=f.read(), file_name="ghg_report.pdf", mime="application/pdf")
