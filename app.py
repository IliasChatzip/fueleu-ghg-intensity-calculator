import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
BASE_TARGET = 91.16  # gCO2eq/MJ reference for 2020
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 2400        # EUR / t VLSFO‑eq
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
    """Return target gCO2eq/MJ for given compliance year."""
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

if st.sidebar.button("🔁 Reset Calculator"):
    st.experimental_rerun()

st.title("FuelEU Maritime - GHG Intensity & Penalty Calculator")
st.sidebar.header("Fuel Inputs")
selected: list[tuple[str, float]] = []

for i in range(1, 6):
    choice = st.sidebar.selectbox(f"Fuel {i}", ["None"] + [f["name"] for f in fuels], key=f"fuel_{i}")
    if choice != "None":
        mass = st.sidebar.number_input(f"{choice} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}")
        if mass > 0:
            selected.append((choice, mass))

ops = st.sidebar.selectbox("OPS Reduction (%)", [0, 1, 2], index=0, help="Reduction applied when using Onshore Power Supply (max 2%)")
wind = st.sidebar.selectbox("Wind Correction Factor", [1.00, 0.99, 0.97, 0.95], index=0, help="Wind-assisted reduction factor (e.g., 0.95 = 5% reduction)")

gwp_choice = st.sidebar.radio(
    "GWP Standard",
    ["AR4 (25/298)", "AR5 (29.8/273)"],
    index=0,
    help="AR4 is the default standard for 2025; AR5 applies from 2026 onward."
)

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

years = list(range(2020, 2051, 5))
targets = [target_intensity(y) for y in years]

gwp = GWP_VALUES["AR4"] if gwp_choice.startswith("AR4") else GWP_VALUES["AR5"]

for name, mt in selected:
    fuel = next(f for f in fuels if f["name"] == name)
    mass_g = mt * 1_000_000
    lcv = fuel["lcv"]
    energy = mass_g * lcv
    ttw_g = fuel["ttw_co2"] + fuel["ttw_ch4"] * gwp["CH4"] + fuel["ttw_n20"] * gwp["N2O"]
    ef = ttw_g / lcv + fuel["wtt"]

  # Apply OPS and wind correction
    ef *= (1 - ops / 100) * wind

    # Apply RFNBO multiplier
    energy_credit = energy * (RFNBO_MULTIPLIER if fuel["rfnbo"] and year <= 2033 else 1)

    totE += energy_credit
    realE += energy  # Actual MJ without multiplier for penalty reference
    emissions += ef * energy

    rows.append({"Fuel": name, "Mass (MT)": mt, "Energy (MJ)": round(energy), "GHG Factor": round(ef, 2), "Emissions (gCO₂eq)": round(ef * energy)})



st.subheader("Fuel Breakdown")
st.dataframe(pd.DataFrame(rows))

st.subheader("Summary")
st.metric("Total Energy (MJ)", f"{totE:,.0f}")
st.metric("Total Emissions (gCO2eq)", f"{emissions:,.0f}")
st.metric("GHG Intensity (gCO2eq/MJ)", f"{emissions / totE:.2f}" if totE else "0.00")
st.metric("Compliance Balance", f"{totE * (target_intensity(year) - (emissions / totE if totE else 0)):,.0f}")
st.metric("Penalty (EUR)", f"{max(0.0, abs(totE * (target_intensity(year) - (emissions / totE if totE else 0))) * PENALTY_RATE / ((emissions / totE if totE else 1) * VLSFO_ENERGY_CONTENT)):,.2f}")

# === TARGET FORECAST CHART ===
st.subheader("Target Intensity Forecast")
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(years, targets, linestyle='--', marker='o')
ax.fill_between(years, targets, alpha=0.2)
for x, y in zip(years, targets):
    ax.annotate(f"{y:.2f}", (x, y), xytext=(0, 5), textcoords="offset points", ha='center')
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
ax.set_title("EU GHG Intensity Targets (2020–2050)")
ax.grid(True)
st.pyplot(fig)
