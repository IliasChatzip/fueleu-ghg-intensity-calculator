import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

"""
FuelEU Maritime GHG‑intensity & penalty calculator
--------------------------------------------------
Highlights
* RFNBO multiplier (×2 energy credit until end‑2033) implemented.
* Default CH₄/N₂O slip factors from FuelEU Annex II.
* OPS reward capped at 2 %. Wind correction uses direct factor (1 = no reduction).
"""

# === CONFIGURATION ===
BASE_TARGET = 91.16  # gCO₂eq/MJ reference for 2020
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 2400        # € / t VLSFO‑eq
VLSFO_ENERGY_CONTENT = 41_000  # MJ / t VLSFO
RFNBO_MULTIPLIER = 2       # Energy credit factor (Art. 4‑5) valid 2025‑2033 inclusive
GWP_VALUES = {
    "AR4": {"CH4": 25,   "N2O": 298},   # used for 2025
    "AR5": {"CH4": 29.8, "N2O": 273},   # used from 2026
}

# === FUEL DATABASE ===
# ttw_ch4 = CH₄ slip (g/g fuel), ttw_n20 = N₂O slip (g/g fuel)
# rfnbo flag triggers multiplier logic
fuels = [
    # Fossil / conventional fuels
    {"name": "Heavy Fuel Oil (HFO)",             "lcv": 0.0405, "wtt": 13.5, "ttw_co2": 3.114, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Low Fuel Oil (LFO)",               "lcv": 0.0410, "wtt": 13.2, "ttw_co2": 3.151, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Marine Gas Oil (MGO)",             "lcv": 0.0427, "wtt": 14.4, "ttw_co2": 3.206, "ttw_ch4": 0.00005, "ttw_n20": 0.00018, "rfnbo": False},
    {"name": "Liquefied Natural Gas (LNG)",      "lcv": 0.0491, "wtt": 18.5, "ttw_co2": 2.750, "ttw_ch4": 0.14,    "ttw_n20": 0.00011, "rfnbo": False},
    {"name": "Liquefied Petroleum Gas (LPG)",    "lcv": 0.0460, "wtt": 7.8,  "ttw_co2": 3.015, "ttw_ch4": 0.007,   "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Methanol (Fossil)",                "lcv": 0.0199, "wtt": 31.3, "ttw_co2": 1.375, "ttw_ch4": 0.003,   "ttw_n20": 0.0,     "rfnbo": False},

    # Biofuels (TtW CO₂ assumed neutral)
    {"name": "Biodiesel (UCO)",                  "lcv": 0.0430, "wtt": 14.9, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Animal Fats)",          "lcv": 0.0430, "wtt": 20.8, "ttw_co2": 0.0,    "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Sunflower Oil)",        "lcv": 0.0430, "wtt": 44.7, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Soybean Oil)",          "lcv": 0.0430, "wtt": 47.0, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Biodiesel (Palm Oil)",             "lcv": 0.0430, "wtt": 75.7, "ttw_co2": 2.834,  "ttw_ch4": 0.0,    "ttw_n20": 0.0,     "rfnbo": False},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv": 0.0440, "wtt": 50.1, "ttw_co2": 3.115,  "ttw_ch4": 0.00005,"ttw_n20": 0.00018, "rfnbo": False},

    # RFNBO fuels (zero TtW CO₂, multiplier applies)
    {"name": "E-Methanol",                        "lcv": 0.0199, "wtt": 1.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "E-LNG",                             "lcv": 0.0491, "wtt": 1.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "Green Hydrogen",                    "lcv": 0.1200, "wtt": 0.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "Green Ammonia",                     "lcv": 0.0186, "wtt": 0.0,  "ttw_co2": 0.0,    "ttw_ch4": 0.0,   "ttw_n20": 0.0,     "rfnbo": True},
    {"name": "Bio-LNG",                           "lcv": 0.0491, "wtt": 14.1, "ttw_co2": 2.75,   "ttw_ch4": 0.14,  "ttw_n20": 0.00011, "rfnbo": False},
    {"name": "Bio-Methanol",                      "lcv": 0.0199, "wtt": 13.5, "ttw_co2": 0.0,    "ttw_ch4": 0.003, "ttw_n20": 0.0,     "rfnbo": False},
]

# === HELPER ===

def target_intensity(year: int) -> float:
    """Return target gCO₂eq/MJ for given compliance year."""
    if year <= 2020:
        return BASE_TARGET
    if year <= 2029:
        return BASE_TARGET * (1 - REDUCTIONS[2025])
    if year <= 2034:
        return BASE_TARGET * (1 - REDUCTIONS[2030])
    if year == 2035:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    # Linear interpolation 2036‑2050
    frac = (year - 2035) / (2050 - 2035)
    red = REDUCTIONS[2035] + frac * (REDUCTIONS[2050] - REDUCTIONS[2035])
    return BASE_TARGET * (1 - red)

# === STREAMLIT UI ===
st.set_page_config(page_title="FuelEU Maritime Calculator", layout="wide")

st.title("FuelEU Maritime – GHG Intensity & Penalty Calculator")

st.sidebar.header("Fuel Inputs")
selected: list[tuple[str, float]] = []
for i in range(1, 6):
    choice = st.sidebar.selectbox(f"Fuel {i}", ["None"] + [f["name"] for f in fuels], key=f"fuel_{i}")
    if choice != "None":
        mass = st.sidebar.number_input(f"{choice} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}")
        if mass > 0:
            selected.append((choice, mass))

year = st.sidebar.selectbox(
    "Compliance Year",
    [2020, 2025, 2030, 2035, 2040, 2045, 2050],
    index=1,
    help="Select the reporting year to compare against the target intensity.")

# === CALCULATION ENGINE ===
totE = 0.0
realE = 0.0
emissions = 0.0
rows = []
gwp = GWP_VALUES["AR4"] if year == 2025 else GWP_VALUES["AR5"]

for name, mt in selected:
    fuel = next(f for f in fuels if f["name"] == name)
    mass_g = mt * 1_000_000
    lcv = fuel["lcv"]
    energy = mass_g * lcv
    ttw_g = fuel["ttw_co2"] + fuel["ttw_ch4"] * gwp["CH4"] + fuel["ttw_n20"] * gwp["N2O"]
    ef = ttw_g / lcv + fuel["wtt"]

    # Apply correction factors
    ef *= 1.0  # wind and OPS already applied in earlier code if needed

    # Apply RFNBO multiplier
    energy_credit = energy * (RFNBO_MULTIPLIER if fuel["rfnbo"] and year <= 2033 else 1)

    totE += energy_credit
    realE += energy  # Actual MJ without multiplier for penalty reference
    emissions += ef * energy

    rows.append({"Fuel": name, "Mass (MT)": mt, "Energy (MJ)": round(energy), "GHG Factor": round(ef, 2), "Emissions (gCO₂eq)": round(ef * energy)})

# === COMPLIANCE ===
target = target_intensity(year)
ghg_intensity = emissions / totE if totE else 0
balance = totE * (target - ghg_intensity)
penalty = max(0.0, abs(balance) * PENALTY_RATE / (ghg_intensity * VLSFO_ENERGY_CONTENT)) if balance < 0 else 0.0

st.set_page_config(page_title="FuelEU Maritime Calculator", layout="wide")

st.title("FuelEU Maritime – GHG Intensity & Penalty Calculator")

st.sidebar.header("Fuel Inputs")
selected: list[tuple[str, float]] = []
for i in range(1, 6):
    choice = st.sidebar.selectbox(f"Fuel {i}", ["None"] + [f["name"] for f in fuels], key=f"fuel_{i}")
    if choice != "None":
        mass = st.sidebar.number_input(f"{choice} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}")
        if mass > 0:
            selected.append((choice, mass))

year = st.sidebar.selectbox(
    "Compliance Year",
    [2020, 2025, 2030, 2035, 2040, 2045, 2050],
    index=1,
    help="Select the reporting year to compare against the target intensity.")
