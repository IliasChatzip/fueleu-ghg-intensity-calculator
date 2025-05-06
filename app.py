import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
BASE_TARGET = 91.16  # Reference target for 2020
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 0.64  # EUR per tonne CO2eq
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273},
}

# === FUEL DATABASE ===
fuels = [
    {"name": "Heavy Fuel Oil (HFO)",  "lcv": 0.0405,  "wtt": 13.5,  "override_ef": 91.73684},
    {"name": "Marine Gas Oil (MGO)",  "lcv": 0.0427,  "wtt": 14.4,  "override_ef": 90.78388}},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv": 0.0410, "wtt": 13.2, "override_ef": 91.39347},
    {"name": "Liquefied Natural Gas (LNG)", "lcv": 0.0500,  "wtt": 79.0},
    {"name": "Liquefied Petroleum Gas (LPG)","lcv": 0.0460,  "wtt": 76.0},
    {"name": "Methanol (Fossil)",           "lcv": 0.0199,  "wtt": 94.0},
    {"name": "Biodiesel (UCO)",            "lcv": 0.03727, "wtt": 14.9},
    {"name": "Biodiesel (Animal Fats)",    "lcv": 0.03727, "wtt": 34.4},
    {"name": "Biodiesel (Sunflower Oil)",  "lcv": 0.03727, "wtt": 45.3},
    {"name": "Biodiesel (Soybean Oil)",   "lcv": 0.03727, "wtt": 56.0},
    {"name": "Biodiesel (Palm Oil)",       "lcv": 0.03727, "wtt": 59.3},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv": 0.0440, "wtt": 22.0},
    {"name": "Bio-LNG",                    "lcv": 0.0500,  "wtt": 10.0},
    {"name": "Bio-Methanol",               "lcv": 0.0199,  "wtt": 11.0},
    {"name": "Green Hydrogen",            "lcv": 0.1200,  "wtt": 0.0},
    {"name": "Green Ammonia",             "lcv": 0.0186,  "wtt": 0.0},
    {"name": "E-Methanol",                "lcv": 0.0199,  "wtt": 1.0},
    {"name": "E-LNG",                     "lcv": 0.0500,  "wtt": 1.0},
    {"name": "Onshore Power Supply (OPS)", "lcv": 1.0000,  "wtt": 0.0},
    {"name": "Synthetic Fuels",           "lcv": 0.0420,  "wtt": 10.0},
    {"name": "Recycled Carbon Fuels (RCFs)", "lcv": 0.0420, "wtt": 70.0},
]

# Compute regulatory target intensity
def target_intensity(year):
    if year <= 2020:
        return BASE_TARGET
    if year <= 2029:
        return BASE_TARGET * (1 - REDUCTIONS[2025])
    if year <= 2034:
        return BASE_TARGET * (1 - REDUCTIONS[2030])
    if year == 2035:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    # Linear to 2050
    y0, r0 = 2035, REDUCTIONS[2035]
    y1, r1 = 2050, REDUCTIONS[2050]
    frac = (year - y0) / (y1 - y0)
    red = r0 + frac * (r1 - r0)
    return BASE_TARGET * (1 - red)

st.title("FuelEU Maritime GHG Intensity Calculator")

# === SIDEBAR INPUTS ===
st.sidebar.header("Fuel Inputs")
selected_fuels = []
for i in range(1, 6):
    choice = st.sidebar.selectbox(f"Fuel {i}", ["None"] + [f["name"] for f in fuels], key=f"fuel_{i}")
    if choice != "None":
        amount = st.sidebar.number_input(f"{choice} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mt_{i}")
        selected_fuels.append((choice, amount))

st.sidebar.markdown("---")
st.sidebar.header("Options")
year = st.sidebar.selectbox(
    "Compliance Year",
    [2020, 2025, 2030, 2035, 2040, 2045, 2050],
    index=1,
    help="Select compliance year (every 5 years from 2020 to 2050)."
)

# Show target for selected year
current_target = target_intensity(year)
st.sidebar.markdown(f"**Target {year}: {current_target:.5f} gCO2eq/MJ**")

gwp_choice = st.sidebar.radio(
    "GWP Standard",
    ["AR4 (25/298)", "AR5 (29.8/273)"],
    index=0,
    help="Use AR4 values for 2025; AR5 applies from 2026"
)
ops = st.sidebar.selectbox("OPS Reduction (%)", [0, 1, 2, 3], index=0)
wind = st.sidebar.selectbox("Wind-Assisted Reduction (%)", [0, 2, 4, 5], index=0)

# === CALCULATION ===
totE = 0.0
totEm = 0.0
rows = []
for name, mt in selected_fuels:
    fuel = next(f for f in fuels if f["name"] == name)
    mass_g = mt * 1_000_000
    energy = mass_g * fuel["lcv"]  # MJ
        # Determine EF (Well-to-Wake)
    if "override_ef" in fuel:
        ef = fuel["override_ef"]
    elif any(keyword in name for keyword in ["Biodiesel", "HVO", "Bio-LNG", "Bio-Methanol", "Green", "E-"]):
        # Biofuels and recycled fuels: no TtW emissions, only WtT
        ef = fuel.get("wtt", 0.0)
    else:
        # Fossil fuels: full dynamic TtW + WtT
        if gwp_choice.startswith("AR4"):
            gwp = GWP_VALUES["AR4"]
        else:
            gwp = GWP_VALUES["AR5"]
        ttw_g_per_g = 3.114 + 0.00005 * gwp["CH4"] + 0.00018 * gwp["N2O"]
        ef = ttw_g_per_g / fuel["lcv"] + fuel.get("wtt", 0.0)
    # Apply rewards
    ef *= (1 - ops/100) * (1 - wind/100)
    emissions = energy * ef
    totE += energy
    totEm += emissions
    rows.append({
        "Fuel": name,
        "Mass (MT)": f"{mt:.2f}",
        "Energy (MJ)": f"{energy:,.2f}",
        "Emissions (gCO2eq)": f"{emissions:,.2f}"
    })

# === OUTPUT ===
st.subheader("Fuel Breakdown")
st.dataframe(pd.DataFrame(rows))

if totE > 0:
    ghg_intensity = totEm / totE
    balance = totE * (current_target - ghg_intensity)
    penalty = 0.0 if balance >= 0 else abs(balance) / 1000 * PENALTY_RATE

    st.subheader("Summary")
    st.metric("Total Energy (MJ)", f"{totE:,.0f}")
    st.metric("Total Emissions (gCO2eq)", f"{totEm:,.0f}")
    st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.5f}")
    st.metric("Compliance Balance (gCO2eq)", f"{balance:,.0f}")
    st.metric("Penalty (€)", f"{penalty:,.2f}")

    # Forecast chart
    years = [2020] + list(range(2025, 2051, 5))
    targets = [BASE_TARGET] + [target_intensity(y) for y in years[1:]]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(years, targets, linestyle='--', marker='o')
    ax.fill_between(years, targets, alpha=0.2)
    for x, y in zip(years, targets):
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 5), ha='center')
    ax.grid(True)
    ax.set_title("GHG Target Forecast (2020–2050)")
    ax.set_xlabel("Year")
    ax.set_ylabel("gCO2eq/MJ")
    plt.tight_layout()
    st.pyplot(fig)
