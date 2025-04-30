# Streamlit Web App: Advanced FuelEU Maritime GHG Intensity Calculator

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === EMISSION FACTORS DATABASE (Expanded) ===
default_fuels = [
    # Fossil Fuels
    {"name": "Heavy Fuel Oil (HFO)", "lcv_mj_per_g": 0.0405, "wtw_gco2_per_mj": (3.114 + 0.00005*29.8 + 0.00018*273)/0.0405 + 13.5},
    {"name": "Marine Gas Oil (MGO)", "lcv_mj_per_g": 0.0427, "wtw_gco2_per_mj": (3.206 + 0.00005*29.8 + 0.00018*273)/0.0427 + 14.4},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv_mj_per_g": 0.041, "wtw_gco2_per_mj": 91.0},
    {"name": "Liquefied Natural Gas (LNG)", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 79.0},
    {"name": "Liquefied Petroleum Gas (LPG)", "lcv_mj_per_g": 0.046, "wtw_gco2_per_mj": 76.0},
    {"name": "Methanol (Fossil)", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 94.0},

    # Biofuels
    {"name": "Biodiesel (UCO)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 14.9},
    {"name": "Biodiesel (Animal Fats)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 34.4},
    {"name": "Biodiesel (Sunflower Oil)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 45.3},
    {"name": "Biodiesel (Soybean Oil)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 56.0},
    {"name": "Biodiesel (Palm Oil - Certified)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 59.3},
    {"name": "Hydrotreated Vegetable Oil (HVO)", "lcv_mj_per_g": 0.044, "wtw_gco2_per_mj": 22.0},
    {"name": "Bio-LNG", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 10.0},
    {"name": "Bio-Methanol", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 11.0},

    # RFNBOs
    {"name": "Green Hydrogen", "lcv_mj_per_g": 0.120, "wtw_gco2_per_mj": 0.0},
    {"name": "Green Ammonia", "lcv_mj_per_g": 0.0186, "wtw_gco2_per_mj": 0.0},
    {"name": "E-Methanol", "lcv_mj_per_g": 0.0199, "wtw_gco2_per_mj": 1.0},
    {"name": "E-LNG", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 1.0},

    # Others
    {"name": "Onshore Power Supply (OPS)", "lcv_mj_per_g": 1.0, "wtw_gco2_per_mj": 0.0},
    {"name": "Synthetic Fuels", "lcv_mj_per_g": 0.042, "wtw_gco2_per_mj": 10.0},
    {"name": "Recycled Carbon Fuels (RCFs)", "lcv_mj_per_g": 0.042, "wtw_gco2_per_mj": 70.0},
]

def get_target_ghg_intensity(year):
    base = 91.16
    reduction = {
        2025: 0.02, 2026: 0.02, 2027: 0.02, 2028: 0.02, 2029: 0.02,
        2030: 0.06, 2031: 0.06, 2032: 0.06, 2033: 0.06, 2034: 0.06,
        2035: 0.14
    }
    return base * (1 - reduction.get(year, 0.0))

def plot_target_trend():
    years = list(range(2025, 2036))
    values = [get_target_ghg_intensity(y) for y in years]
    fig, ax = plt.subplots()
    ax.plot(years, values, marker='o')
    ax.set_title("FuelEU Target GHG Intensity Forecast")
    ax.set_ylabel("gCO2eq/MJ")
    ax.set_xlabel("Year")
    ax.grid(True)
    st.pyplot(fig)

st.title("FuelEU Maritime GHG Intensity Calculator")

plot_target_trend()

# === USER INPUTS ===
st.sidebar.header("Fuel Input")
fuel_defaults = pd.DataFrame(default_fuels)
selected_fuels = []

for i in range(1, 6):
    fuel_type = st.sidebar.selectbox(f"Fuel {i} type", ["None"] + list(fuel_defaults["name"]), index=0, key=f"fuel_{i}_type")
    if fuel_type != "None":
        mode = st.sidebar.radio(f"Use default or custom values for {fuel_type}?", ["Default", "Custom"], key=f"mode_{i}")
        mass = st.sidebar.number_input(f"{fuel_type} mass (MT)", min_value=0.0, value=0.0, step=100.0, key=f"mass_{i}")
        if mass > 0:
            if mode == "Custom":
                lcv = st.sidebar.number_input(f"LCV for {fuel_type} (MJ/g)", value=0.04, key=f"lcv_{i}")
                ef = st.sidebar.number_input(f"WtW EF for {fuel_type} (gCO₂eq/MJ)", value=90.0, key=f"ef_{i}")
            else:
                entry = fuel_defaults[fuel_defaults.name == fuel_type].iloc[0]
                lcv, ef = entry['lcv_mj_per_g'], entry['wtw_gco2_per_mj']
            selected_fuels.append({"name": fuel_type, "mass_mt": mass, "lcv": lcv, "ef": ef})

st.sidebar.markdown("---")
year = st.sidebar.selectbox("Compliance Year", list(range(2025, 2036)))
target_ghg_intensity = get_target_ghg_intensity(year)

ops_discount = st.sidebar.selectbox(
    "OPS Reduction (%)",
    [0, 1, 2, 3],
    index=0,
    help="Reward for use of Onshore Power Supply (OPS) during port stays. Max 3% emissions reduction allowed."
)
wind_discount = st.sidebar.selectbox(
    "Wind-Assisted Reduction (%)",
    [0, 2, 4, 5],
    index=0,
    help="Reward for using wind propulsion assistance. Reduction reflects certified propulsion effectiveness."
)

# === CALCULATIONS ===
total_energy = 0.0
total_emissions = 0.0
fuel_rows = []
penalty_per_mj = 2.4 / 1000

for fuel in selected_fuels:
    mass_g = fuel['mass_mt'] * 1_000_000
    energy = mass_g * fuel['lcv']
    emissions = energy * fuel['ef']
    total_energy += energy
    total_emissions += emissions
    fuel_rows.append({
        "Fuel": fuel['name'],
        "Mass (MT)": f"{fuel['mass_mt']:.2f}",
        "Energy (MJ)": f"{energy:,.2f}",
        "Emissions (gCO₂eq)": f"{emissions:,.2f}"
    })

if ops_discount > 0:
    total_emissions *= (1 - ops_discount / 100)
if wind_discount > 0:
    total_emissions *= (1 - wind_discount / 100)

# === OUTPUT ===
import io

if fuel_rows:
    st.subheader("Fuel Breakdown")
    df_fuel = pd.DataFrame(fuel_rows)
    st.dataframe(df_fuel)

    ghg_intensity = total_emissions / total_energy if total_energy > 0 else 0
    balance = total_energy * (target_ghg_intensity - ghg_intensity)
    penalty = 0.0 if balance >= 0 else abs(balance) * penalty_per_mj

    st.subheader("Summary")
    st.metric("Total Energy (MJ)", f"{total_energy:,.0f}")
    st.metric("Total Emissions (gCO₂eq)", f"{total_emissions:,.0f}")
    st.metric("GHG Intensity (gCO₂eq/MJ)", f"{ghg_intensity:.5f}")
    st.metric("Compliance Balance (gCO₂eq)", f"{balance:,.0f}")
    st.metric("Penalty (€)", f"{penalty:,.2f}")

    if penalty == 0 and balance > 0:
        surplus_eur = (balance / 1000) * 2.4
        st.success(f"Over-compliance credit: {surplus_eur:,.2f} EUR for {balance:,.0f} gCO2eq below target")

    # Export to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_fuel.to_excel(writer, index=False, sheet_name='Fuel Breakdown')
        pd.DataFrame([{
            "Total Energy (MJ)": total_energy,
            "Total Emissions (gCO2eq)": total_emissions,
            "GHG Intensity": ghg_intensity,
            "Compliance Balance": balance,
            "Penalty (EUR)": penalty
        }]).to_excel(writer, index=False, sheet_name='Summary')
    output.seek(0)
    
    # Export to PDF
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="FuelEU Maritime GHG Summary", ln=True, align='C')
    pdf.ln(10)
    for key, val in {
        "Total Energy (MJ)": total_energy,
        "Total Emissions (gCO2eq)": total_emissions,
        "GHG Intensity (gCO2eq/MJ)": ghg_intensity,
        "Compliance Balance (gCO2eq)": balance,
        "Penalty (€)": penalty
    }.items():
        pdf.cell(200, 10, txt=f"{key}: {val:.2f}", ln=True)
    pdf_output = pdf.output(dest='S').encode('latin-1', errors='replace')
    st.download_button(
        label="Download Results as PDF",
        data=pdf_output,
        file_name="fueleu_ghg_summary.pdf",
        mime="application/pdf"
    )

    st.download_button(
        
        label="Download Results as Excel",
        data=output,
        file_name="fueleu_ghg_calculation.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please enter fuel inputs in the sidebar to see results.")
