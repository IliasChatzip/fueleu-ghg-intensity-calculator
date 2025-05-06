import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
BASE_TARGET = 91.16  # Reference GHG intensity for 2020
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 1428  # EUR per tonne VLSFO equivalent
VLSFO_ENERGY_CONTENT = 41000  # MJ per tonne VLSFO
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273}
}

# === FUEL DATABASE ===
fuels = [
    {"name": "Heavy Fuel Oil (HFO)",            "lcv": 0.0405, "wtt": 13.5, "ttw_co2": 3.114},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)","lcv": 0.0410, "wtt": 13.2, "ttw_co2": 3.188},
    {"name": "Marine Gas Oil (MGO)",            "lcv": 0.0427, "wtt": 14.4, "ttw_co2": 3.206},
    {"name": "Liquefied Natural Gas (LNG)",     "lcv": 0.0500, "wtt": 79.0,  "ttw_co2": 2.750},
    {"name": "Liquefied Petroleum Gas (LPG)",   "lcv": 0.0460, "wtt": 76.0,  "ttw_co2": 3.000},
    {"name": "Methanol (Fossil)",               "lcv": 0.0199, "wtt": 94.0,  "ttw_co2": 1.375},
    {"name": "Biodiesel (UCO)",                "lcv": 0.03727, "wtt": 14.9, "ttw_co2": 0.0},
    {"name": "Biodiesel (Animal Fats)",        "lcv": 0.03727, "wtt": 34.4, "ttw_co2": 0.0},
    {"name": "Biodiesel (Sunflower Oil)",      "lcv": 0.03727, "wtt": 45.3, "ttw_co2": 0.0},
    {"name": "Biodiesel (Soybean Oil)",        "lcv": 0.03727, "wtt": 56.0, "ttw_co2": 0.0},
    {"name": "Biodiesel (Palm Oil)",           "lcv": 0.03727, "wtt": 59.3, "ttw_co2": 0.0},
    {"name": "Hydrotreated Vegetable Oil (HVO)","lcv": 0.0440, "wtt": 22.0, "ttw_co2": 0.0},
    {"name": "Bio-LNG",                        "lcv": 0.0500, "wtt": 10.0,  "ttw_co2": 0.0},
    {"name": "Bio-Methanol",                   "lcv": 0.0199, "wtt": 11.0,  "ttw_co2": 0.0},
    {"name": "Green Hydrogen",                 "lcv": 0.1200, "wtt": 0.0,   "ttw_co2": 0.0},
    {"name": "Green Ammonia",                  "lcv": 0.0186, "wtt": 0.0,   "ttw_co2": 0.0},
    {"name": "E-Methanol",                     "lcv": 0.0199, "wtt": 1.0,   "ttw_co2": 0.0},
    {"name": "E-LNG",                          "lcv": 0.0500, "wtt": 1.0,   "ttw_co2": 0.0},
    {"name": "Onshore Power Supply (OPS)",     "lcv": 1.0000, "wtt": 0.0,   "ttw_co2": 0.0},
    {"name": "Synthetic Fuels",                "lcv": 0.0420, "wtt": 10.0,  "ttw_co2": 2.900},
    {"name": "Recycled Carbon Fuels (RCFs)",   "lcv": 0.0420, "wtt": 70.0,  "ttw_co2": 2.900},
]

# === FUNCTION TO COMPUTE TARGET INTENSITY ===
def target_intensity(year):
    if year <= 2020:
        return BASE_TARGET
    if year <= 2029:
        return BASE_TARGET * (1 - REDUCTIONS[2025])
    if year <= 2034:
        return BASE_TARGET * (1 - REDUCTIONS[2030])
    if year == 2035:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    y0, r0 = 2035, REDUCTIONS[2035]
    y1, r1 = 2050, REDUCTIONS[2050]
    frac = (year - y0) / (y1 - y0)
    red = r0 + frac * (r1 - r0)
    return BASE_TARGET * (1 - red)

# === STREAMLIT INTERFACE ===
st.title("FuelEU Maritime GHG Intensity Calculator")

st.sidebar.header("Fuel Inputs")
selected = []
for i in range(1, 6):
    choice = st.sidebar.selectbox(f"Fuel {i}", ["None"] + [f["name"] for f in fuels], key=f"fuel_{i}")
    if choice != "None":
        mass = st.sidebar.number_input(f"{choice} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}")
        if mass > 0:
            selected.append((choice, mass))

year = st.sidebar.selectbox("Compliance Year", [2020, 2025, 2030, 2035, 2040, 2045, 2050], index=1)
target = target_intensity(year)
st.sidebar.markdown(f"**Target {year}: {target:.5f} gCO₂eq/MJ**")

gwp_choice = st.sidebar.radio("GWP Standard", ["AR4 (25/298)", "AR5 (29.8/273)"], index=0)
ops = st.sidebar.selectbox("OPS Reduction (%)", [0,1,2,3], index=0)
wind = st.sidebar.selectbox("Wind-Assisted Reduction (%)", [0,2,4,5], index=0)

# === CALCULATION ===
totE = 0.0
totEm = 0.0
rows = []
gwp = GWP_VALUES["AR4"] if gwp_choice.startswith("AR4") else GWP_VALUES["AR5"]
for name, mt in selected:
    fuel = next(f for f in fuels if f["name"] == name)
    mass_g = mt * 1_000_000
    energy = mass_g * fuel["lcv"]
    if fuel["ttw_co2"] == 0.0:
        ef = fuel["wtt"]
    else:
        ttw_g = fuel["ttw_co2"] + 0.00005 * gwp["CH4"] + 0.00018 * gwp["N2O"]
        ttw_mj = ttw_g / fuel["lcv"]
        ef = ttw_mj + fuel["wtt"]
    ef *= (1 - ops/100) * (1 - wind/100)
    emissions = energy * ef
    totE += energy
    totEm += emissions
    rows.append({"Fuel": name, "Mass (MT)": f"{mt:.2f}", "Energy (MJ)": f"{energy:,.2f}", "Emissions (gCO₂eq)": f"{emissions:,.2f}"})

# === OUTPUT ===
st.subheader("Fuel Breakdown")
st.dataframe(pd.DataFrame(rows))

if totE > 0:
    ghg_int = totEm / totE
    balance = totE * (target - ghg_int)
    penalty = 0.0 if balance >= 0 else abs(balance) * PENALTY_RATE / (ghg_int * VLSFO_ENERGY_CONTENT)

    st.subheader("Summary")
    st.metric("Total Energy (MJ)", f"{totE:,.0f}")
    st.metric("Total Emissions (gCO₂eq)", f"{totEm:,.0f}")
    st.metric("GHG Intensity (gCO₂eq/MJ)", f"{ghg_int:.5f}")
    st.metric("Compliance Balance (gCO₂eq)", f"{balance:,.0f}")
    st.metric("Penalty (€)", f"{penalty:,.2f}")

    years = [2020] + list(range(2025, 2051, 5))
    targets = [BASE_TARGET] + [target_intensity(y) for y in years[1:]]
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(years, targets, linestyle='--', marker='o')
    ax.fill_between(years, targets, alpha=0.2)
    for x,y in zip(years, targets):
        ax.annotate(f"{y:.2f}",(x,y),xytext=(0,5),textcoords="offset points",ha='center')
    ax.grid(True)
    ax.set_title("GHG Target Forecast (2020–2050)")
    ax.set_xlabel("Year")
    ax.set_ylabel("gCO₂eq/MJ")
    plt.tight_layout()
    st.pyplot(fig)
