import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from fpdf import FPDF
from datetime import datetime
import tempfile
import os

    
# === PAGE CONFIG ===
st.set_page_config(page_title="FuelEU GHG Calculator", layout="wide")

# === STABLE RESET HANDLER ===
def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]  # Clear all session state
    st.session_state["trigger_reset"] = False
    st.stop()  # Halt this run; will auto-rerun clean

# === Check if Reset Was Triggered
if st.session_state.get("trigger_reset", False):
    reset_app()

# === Sidebar Reset Button
st.sidebar.button("🔁 Reset Calculator", on_click=lambda: st.session_state.update({"trigger_reset": True}))


# === CONFIGURATION ===
BASE_TARGET = 91.16
REDUCTIONS = {2025: 0.02, 2030: 0.06, 2035: 0.14, 2050: 0.80}
PENALTY_RATE = 2400
VLSFO_ENERGY_CONTENT = 41_000
REWARD_FACTOR_NBO_MULTIPLIER = 2
GWP_VALUES = {
    "AR4": {"CH4": 25, "N2O": 298},
    "AR5": {"CH4": 29.8, "N2O": 273},}

# === FUEL DATABASE ===
FUELS = [
    {"name": "Heavy Fuel Oil (HFO)",                                    "lcv": 0.0405, "wtt": 13.5,  "ttw_co2": 3.114, "ttw_ch4": 0.00005, "ttw_n20": 0.00018,  "nbo": False},
    {"name": "Low Fuel Oil (LFO)",                                      "lcv": 0.0410, "wtt": 13.2,  "ttw_co2": 3.151, "ttw_ch4": 0.00005, "ttw_n20": 0.00018,  "nbo": False},
    {"name": "Marine Gas Oil (MGO)",                                    "lcv": 0.0427, "wtt": 14.4,  "ttw_co2": 3.206, "ttw_ch4": 0.00005, "ttw_n20": 0.00018,  "nbo": False},
    {"name": "Liquefied Natural Gas (LNG)",                             "lcv": 0.0491, "wtt": 18.5,  "ttw_co2": 2.750, "ttw_ch4": 0.001276,"ttw_n20": 0.00011,  "nbo": False},
    {"name": "Liquefied Petroleum Gas (LPG)",                           "lcv": 0.0460, "wtt": 7.8,   "ttw_co2": 3.015, "ttw_ch4": 0.007,   "ttw_n20": 0.0,      "nbo": False},
    {"name": "Methanol (Fossil)",                                       "lcv": 0.0199, "wtt": 31.3,  "ttw_co2": 1.375, "ttw_ch4": 0.003,   "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (Rapeseed Oil,B100)",                           "lcv": 0.0430, "wtt": 1.5,   "ttw_co2": 2.834, "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (Corn Oil,B100)",                               "lcv": 0.0430, "wtt": 31.6,  "ttw_co2": 2.834, "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (Wheat Straw,B100)",                            "lcv": 0.0430, "wtt": 15.7,  "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Bioethanol (Sugar Beet)",                                 "lcv": 0.027,  "wtt": 35.0,  "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Bioethanol (Maize)",                                      "lcv": 0.027,  "wtt": 38.2,  "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Bioethanol (Wheat)",                                      "lcv": 0.027,  "wtt": 41.0,  "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (UCO,B100)",                                    "lcv": 0.0430, "wtt": 14.9,  "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (Animal Fats,B100)",                            "lcv": 0.0430, "wtt": 20.8,  "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (Sunflower Oil,B100)",                          "lcv": 0.0430, "wtt": 44.7,  "ttw_co2": 2.834, "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (Soybean Oil,B100)",                            "lcv": 0.0430, "wtt": 47.0,  "ttw_co2": 2.834, "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Biodiesel (Palm Oil,B100)",                               "lcv": 0.0430, "wtt": 75.7,  "ttw_co2": 2.834, "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Hydrotreated Vegetable Oil (HVO from rape seed,HVO100)",  "lcv": 0.0440, "wtt": 50.1,  "ttw_co2": 3.115, "ttw_ch4": 0.00005, "ttw_n20": 0.00018,  "nbo": False},
    {"name": "Hydrotreated Vegetable Oil (HVO from sunflower,HVO100)",  "lcv": 0.0440, "wtt": 43.6,  "ttw_co2": 3.115, "ttw_ch4": 0.00005, "ttw_n20": 0.00018,  "nbo": False},    
    {"name": "Hydrotreated Vegetable Oil (HVO from soybean,HVO100)",    "lcv": 0.0440, "wtt": 46.5,  "ttw_co2": 3.115, "ttw_ch4": 0.00005, "ttw_n20": 0.00018,  "nbo": False},  
    {"name": "Hydrotreated Vegetable Oil (HVO from palm oil,HVO100)",   "lcv": 0.0440, "wtt": 73.3,  "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Fossil Hydrogen",                                         "lcv": 0.1200, "wtt": 132.7, "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "Fossil Ammonia",                                          "lcv": 0.0186, "wtt": 118.6, "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": False},
    {"name": "E-Methanol",                                              "lcv": 0.0199, "wtt": 1.0,   "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": True},
    {"name": "E-LNG",                                                   "lcv": 0.0491, "wtt": 1.0,   "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": True},
    {"name": "Green Hydrogen",                                          "lcv": 0.1200, "wtt": 0.0,   "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": True},
    {"name": "Green Ammonia",                                           "lcv": 0.0186, "wtt": 0.0,   "ttw_co2": 0.0,   "ttw_ch4": 0.0,     "ttw_n20": 0.0,      "nbo": True},
    {"name": "Bio-LNG",                                                 "lcv": 0.0491, "wtt": 14.1,  "ttw_co2": 2.75,  "ttw_ch4": 0.14,    "ttw_n20": 0.00011,  "nbo": False},
    {"name": "Bio-Methanol",                                            "lcv": 0.0199, "wtt": 13.5,  "ttw_co2": 0.0,   "ttw_ch4": 0.003,   "ttw_n20": 0.0,      "nbo": False},  
]

# === TARGET FUNCTION ===
def target_intensity(year: int) -> float:
    if year <= 2020:
        return BASE_TARGET
    if year <= 2029:
        return BASE_TARGET * (1 - REDUCTIONS[2025])
    if year <= 2034:
        return BASE_TARGET * (1 - REDUCTIONS[2030])
    if year == 2035:
        return BASE_TARGET * (1 - REDUCTIONS[2035])
    frac = (year - 2035) / (2050 - 2035)
    red = REDUCTIONS[2035] + frac * (REDUCTIONS[2050] - REDUCTIONS[2035])
    return BASE_TARGET * (1 - red)

    
# === USER INPUT ===
st.title("FuelEU - GHG Intensity & Penalty Calculator")
st.sidebar.subheader("Fuel Inputs")
fuel_inputs = {}

categories = {
    "Fossil ": [f for f in FUELS if not f['nbo'] and "Bio" not in f['name'] and "Biodiesel" not in f['name'] and "E-" not in f['name'] and "Green" not in f['name']],
    "Bio": [f for f in FUELS if "Bio" in f['name'] or "Biodiesel" in f['name']],
    "NBO": [f for f in FUELS if f['nbo'] or "E-" in f['name'] or "Green" in f['name']]
}

for category, fuels_in_cat in categories.items():
    with st.sidebar.expander(f"{category} Fuels", expanded=False):
        selected_fuels = st.multiselect(f"Select {category} Fuels", [f["name"] for f in fuels_in_cat], key=f"multiselect_{category}")
        for selected_fuel in selected_fuels:
            qty = st.number_input(f"{selected_fuel} (t)", min_value=0, step=1, value=0, format="%d", key=f"qty_{selected_fuel}")
            fuel_inputs[selected_fuel] = qty

st.sidebar.markdown("---")
st.sidebar.header("Input Parameters")

year = st.sidebar.selectbox(
    "Compliance Year",
    [2020, 2025, 2030, 2035, 2040, 2045, 2050],
    index=1,
    help="Select the reporting year to compare against the target intensity."
)

gwp_choice = st.sidebar.radio(
    "GWP Standard",
    ["AR4", "AR5"],
    index=0,
    help="Choose Global Warming Potential values: AR4 (CH₄: 25, N₂O: 298) or AR5 (CH₄: 29.8, N₂O: 273)."
)
gwp = GWP_VALUES[gwp_choice]

ops = st.sidebar.selectbox(
    "OPS Reward Factor (%)",
    [0, 1, 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20],
    index=0,
    help="This is a reward factor of a ship which utilise the electricity from offshore power supply (OPS) connection point. This input is the percentage of electricity delivered to the ship per total amount of energy consumption onboard (max 20%)."
)

wind = st.sidebar.selectbox(
    "Wind Reward Factor",
    [1.00, 0.99, 0.97, 0.95],
    index=0,
    help="This is a reward factor wind-assisted propulsion if it is installed onboard. Reference can be made to the Regulation (EU) 2023/1805 of The European Parliament and of The Counsil. In case of no wind-assisted propulsion onboard, Wind Reward Factor of 1 can be selected (lower = more assistance)."
)
    
# === CALCULATIONS ===
total_energy = 0.0
emissions = 0.0
rows = []

for fuel in FUELS:
    qty = fuel_inputs.get(fuel["name"], 0.0)
    if qty > 0:
        mass_g = qty * 1_000_000
        lcv = fuel["lcv"]
        energy = mass_g * lcv
        if fuel["nbo"] and year <= 2033:
            energy *= REWARD_FACTOR_NBO_MULTIPLIER
            
        co2_total = fuel["ttw_co2"] * mass_g * (1 - ops / 100) * wind
        ch4_total = fuel["ttw_ch4"] * mass_g * gwp["CH4"]
        n2o_total = fuel["ttw_n20"] * mass_g * gwp["N2O"]
        ttw_total = co2_total + ch4_total + n2o_total
        wtt_total = energy * fuel["wtt"]
        total_emissions = ttw_total + wtt_total
            
        total_energy += energy
        emissions += total_emissions
        
        ghg_intensity_mj = total_emissions / energy if energy else 0
        
        rows.append({
            "Fuel": fuel["name"],
            "Quantity (t)": qty,
            "Energy (MJ)": energy,
            "GHG Intensity (gCO2eq/MJ)": ghg_intensity_mj,
            "Emissions (gCO2eq)": total_emissions,
        })
        
# after all fuels processed
ghg_intensity = emissions / total_energy if total_energy else 0.0
st.session_state["computed_ghg"] = ghg_intensity

compliance_balance = total_energy * (target_intensity(year) - ghg_intensity)
        
if compliance_balance >= 0:
     penalty = 0
else:
     penalty = (abs(compliance_balance) / (ghg_intensity * VLSFO_ENERGY_CONTENT)) * PENALTY_RATE

# === OUTPUT ===
st.subheader("Fuel Breakdown")
if rows:
    df_raw = pd.DataFrame(rows).sort_values("Emissions (gCO2eq)", ascending=False).reset_index(drop=True)
    df_formatted = df_raw.style.format({
        "Quantity (t)": "{:,.0f}",
        "Energy (MJ)": "{:,.0f}",
        "Emissions (gCO2eq)": "{:,.0f}",
        "GHG Intensity (gCO2eq/MJ)": "{:,.2f}"
    })
    st.dataframe(df_formatted)
else:
    st.info("No fuel data provided yet. Please select fuel(s) and enter quantity.")

st.subheader("Summary")
st.metric("GHG Intensity (gCO2eq/MJ)", f"{ghg_intensity:.2f}")
balance_label = "Surplus" if compliance_balance >= 0 else "Deficit"
st.metric("Compliance Balance (MJ)", f"{compliance_balance:,.0f}")
st.metric("Estimated Penalty (Eur)", f"{penalty:,.2f}")

# === MITIGATION OPTIONS ===
if penalty > 0:
    st.subheader("Mitigation Options (Penalty Offset)")
    mitigation_rows = []

    for fuel in FUELS:
        # Skip fuels already used in input
        if fuel["name"] in fuel_inputs and fuel_inputs[fuel["name"]] > 0:
            continue
        
        # Calculate GHG intensity of the fuel
        co2_mj = fuel["ttw_co2"] * (1 - ops / 100) * wind
        ch4_mj = fuel["ttw_ch4"] * gwp["CH4"]
        n2o_mj = fuel["ttw_n20"] * gwp["N2O"]
        ttw = co2_mj + ch4_mj + n2o_mj
        total_ghg_per_mj = fuel["wtt"] + ttw

        delta = ghg_intensity - total_ghg_per_mj
        if delta <= 0:
            continue  # Not a beneficial fuel

        req_energy_mj = abs(compliance_balance) / delta
        required_mass_g = req_energy_mj / fuel["lcv"]
        required_tonnes = required_mass_g / 1_000_000

        mitigation_rows.append({
            "Fuel": fuel["name"],
            "Required Amount (t)": required_tonnes,
        })

    if mitigation_rows:
        df_mitigation = pd.DataFrame(mitigation_rows).sort_values("Required Amount (t)").reset_index(drop=True)
        st.dataframe(df_mitigation.style.format({"Required Amount (t)": "{:,.0f}"}))
    else:
        st.info("No effective fuels found to offset the penalty based on current configuration.")

# === COMPLIANCE CHART ===
years = list(range(2020, 2051, 5))
targets = [target_intensity(y) for y in years]

st.subheader("Sector-wide GHG Intensity Targets")
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(years, targets, linestyle='--', marker='o', label='EU Target')
ax.axhline(st.session_state["computed_ghg"], color='red', linestyle='-', label='Your GHG Intensity')
ax.set_xlabel("Year")
ax.set_ylabel("gCO2eq/MJ")
ax.set_title("Your Performance vs Sector Target")
ax.legend()
ax.grid(True)
st.pyplot(fig)


# === PDF EXPORT ===
if st.button("Export to PDF"):
    if not rows:
        st.warning("No data to export.")
    else:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Fuel EU Maritime GHG & Penalty Report", ln=True, align="C")
        pdf.cell(200, 10, txt=f"Year: {year} | GWP: {gwp_choice}", ln=True)
        pdf.cell(200, 10, txt=f"GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ", ln=True)
        pdf.cell(200, 10, txt=f"Compliance Balance: {compliance_balance:,.0f} MJ", ln=True)
        pdf.cell(200, 10, txt=f"Penalty: {penalty:,.2f} Eur", ln=True)
        pdf.ln(10)        
        for row in rows:
            line = f"{row['Fuel']}: {row['Quantity (t)']:,.0f} t | {row['Energy (MJ)']:,.0f} MJ | {row['Emissions (gCO2eq)']:,.0f} g"
            pdf.cell(200, 10, txt=line, ln=True)
            
        if penalty > 0 and 'df_mitigation' in locals():
             pdf.ln(5)
             pdf.cell(200, 10, txt="--- Mitigation Options ---", ln=True)
             for row in mitigation_rows:
                 mit_line = f"{row['Fuel']}: {row['Required Amount (t)']:,.2f} t"
                 pdf.cell(200, 10, txt=mit_line, ln=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            tmp_pdf_path = tmp_pdf.name            
        st.success(f"PDF exported: {os.path.basename(tmp_pdf_path)}")
        st.download_button("Download PDF", data=open(tmp_pdf_path, "rb"), file_name="ghg_report.pdf", mime="application/pdf")
