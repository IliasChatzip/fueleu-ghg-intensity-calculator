import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION ===
# Global Warming Potentials for scope calculations
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273}
}
PENALTY_RATE = 0.64  # EUR per tonne CO2eq

# === FUEL DATABASE ===
fuels = [
    {"name": "Heavy Fuel Oil (HFO)", "lcv": 0.0405, "wtt": 13.5},
    {"name": "Marine Gas Oil (MGO)", "lcv": 0.0427, "wtt": 14.4},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv": 0.041, "wtt": 13.5},
    {"name": "Liquefied Natural Gas (LNG)", "lcv": 0.050, "wtt": 79.0},
    {"name": "Liquefied Petroleum Gas (LPG)", "lcv": 0.046, "wtt": 76.0},
    {"name": "Methanol (Fossil)", "lcv": 0.0199, "wtt": 94.0},
    {"name": "Biodiesel (UCO)", "lcv": 0.03727, "wtt": 14.9},
    {"name": "Biodiesel (Animal Fats)", "lcv": 0.03727, "wtt": 34.4},
    {"name": "Biodiesel (Sunflower Oil)", "lcv": 0.03727, "wtt": 45.3},
    {"name": "Biodiesel (Soybean Oil)", "lcv": 0.03727, "wtt": 56.0},
    {"name": "Biodiesel (Palm Oil - Certified)", "lcv": 0.03727, "wtt": 59.3},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv": 0.044, "wtt": 22.0},
    {"name": "Bio-LNG", "lcv": 0.050, "wtt": 10.0},
    {"name": "Bio-Methanol", "lcv": 0.0199, "wtt": 11.0},
    {"name": "Green Hydrogen", "lcv": 0.120, "wtt": 0.0},
    {"name": "Green Ammonia", "lcv": 0.0186, "wtt": 0.0},
    {"name": "E-Methanol", "lcv": 0.0199, "wtt": 1.0},
    {"name": "E-LNG", "lcv": 0.050, "wtt": 1.0},
    {"name": "Onshore Power Supply (OPS)", "lcv": 1.0, "wtt": 0.0},
    {"name": "Synthetic Fuels", "lcv": 0.042, "wtt": 10.0},
    {"name": "Recycled Carbon Fuels (RCFs)", "lcv": 0.042, "wtt": 70.0},
]

# === HELPERS ===
def get_target_ghg_intensity(year):
    base = 91.16
    if year < 2025:
        return base
    if year <= 2029:
        return base * (1 - 0.02)
    if year <= 2034:
        return base * (1 - 0.06)
    if year == 2035:
        return base * (1 - 0.14)
    # Linear interpolation to 80% reduction by 2050
    reduction = 0.14 + (0.80 - 0.14) * (year - 2035) / (2050 - 2035)
    return base * (1 - reduction)

# === APP LAYOUT ===
st.title("FuelEU Maritime GHG Intensity Calculator")

# Sidebar: Fuel Inputs (always on top)
st.sidebar.header("Fuel Inputs")
selected_fuels = []
for fuel in fuels:
    mt = st.sidebar.number_input(
        f"{fuel['name']} (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mt_{fuel['name']}"
    )
    if mt > 0:
        selected_fuels.append({**fuel, "mt": mt})

# Sidebar Options
st.sidebar.markdown("---")
ghg_scope = st.sidebar.radio(
    "GHG Scope",
    ["CO2 only", "Full scope (AR4)", "Full scope (AR5)"],
    index=1,
    help="Choose CO2-only or full TtW scope using AR4 (2025) or AR5 (2026+)."
)
year = st.sidebar.selectbox("Compliance Year", list(range(2020, 2051)), index=year - 2020 if (year := 2025) else 5)
ops = st.sidebar.selectbox("OPS Reduction (%)", [0, 1, 2, 3], index=0)
wind = st.sidebar.selectbox("Wind-Assisted Reduction (%)", [0, 2, 4, 5], index=0)
pooling = st.sidebar.checkbox(
    "Simulate pooling/trading of surplus", value=False,
    help="Allow over-compliance surplus to be used in pooling or credit transfers."
)

# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
fuel_rows = []
for f in selected_fuels:
    mass_g = f['mt'] * 1_000_000
    energy = mass_g * f['lcv']
    # Determine TtW per gram
    if ghg_scope == "CO2 only":
        ttw_g = 3.114
    else:
        gwp_key = "AR4" if ghg_scope.endswith("AR4)") else "AR5"
        ttw_g = 3.114 + 0.00005 * GWP_VALUES[gwp_key]["CH4"] + 0.00018 * GWP_VALUES[gwp_key]["N2O"]
    # Compute EF per MJ
    ef = ttw_g / f['lcv'] + f['wtt']
    emissions = energy * ef
    total_energy += energy
    total_emissions += emissions
    fuel_rows.append({
        "Fuel": f['name'],
        "Mass (MT)": f['mt'],
        "Energy (MJ)": round(energy, 2),
        "Emissions (gCO2eq)": round(emissions, 2)
    })
# Apply OPS and Wind rewards
reward_factor = (1 - ops / 100) * (1 - wind / 100)
final_emissions = total_emissions * reward_factor

# === OUTPUT ===
if fuel_rows:
    st.subheader("Fuel Breakdown")
    st.dataframe(pd.DataFrame(fuel_rows))

    target = get_target_ghg_intensity(year)
    ghg_intensity = final_emissions / total_energy if total_energy else 0
    balance = (target - ghg_intensity) * total_energy
    penalty = 0.0 if balance >= 0 else abs(balance) / 1000 * PENALTY_RATE

    st.subheader("Summary")
    st.metric("Total Energy (MJ)", f"{total_energy:,.0f}")
    st.metric("Total Emissions (gCO2eq)", f"{final_emissions:,.0f}")
    st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.5f}")
    st.metric("Target GHG Intensity (gCO2eq/MJ)", f"{target:.5f}")
    st.metric("Compliance Balance (gCO2eq)", f"{balance:,.0f}")
    st.metric("Penalty (EUR)", f"{penalty:,.2f}")

    if penalty == 0 and pooling:
        surplus = balance / 1000 * 2.4
        st.success(
            f"Surplus margin: {surplus:,.2f} EUR for {balance:,.0f} gCO2eq below target."
        )

    # Forecast chart
    years_line = [2020] + list(range(2025, 2051, 5))
    vals = [91.16] + [get_target_ghg_intensity(y) for y in years_line[1:]]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(years_line, vals, linestyle='--', marker='o')
    ax.fill_between(years_line, vals, alpha=0.2)
    for x, y in zip(years_line, vals):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 5), ha='center')
    ax.set_xlabel("Year")
    ax.set_ylabel("GHG Target (gCO2eq/MJ)")
    ax.set_title("GHG Target Forecast (2020–2050, 5-year intervals)")
    ax.grid(True)
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.info("Enter at least one fuel quantity to see results.")
