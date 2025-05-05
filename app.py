import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === EMISSION FACTORS DATABASE ===
default_fuels = [
    {"name": "Heavy Fuel Oil (HFO)", "lcv_mj_per_g": 0.0405, "wtw_gco2_per_mj": (3.114 + 0.00005*25 + 0.00018*298)/0.0405 + 13.5},
    {"name": "Marine Gas Oil (MGO)", "lcv_mj_per_g": 0.0427, "wtw_gco2_per_mj": (3.206 + 0.00005*25 + 0.00018*298)/0.0427 + 14.4},
    {"name": "Very Low Sulphur Fuel Oil (VLSFO)", "lcv_mj_per_g": 0.041, "wtw_gco2_per_mj": 91.0},
    {"name": "Liquefied Natural Gas (LNG)", "lcv_mj_per_g": 0.050, "wtw_gco2_per_mj": 79.0},
    {"name": "Biodiesel (UCO)", "lcv_mj_per_g": 0.03727, "wtw_gco2_per_mj": 14.9}
]

# === TARGET CALCULATION ===
def get_target_ghg_intensity(year):
    base = 91.16
    reductions = {2025:0.02,2026:0.02,2027:0.02,2028:0.02,2029:0.02,
                  2030:0.06,2031:0.06,2032:0.06,2033:0.06,2034:0.06,2035:0.14}
    if year in reductions:
        return base*(1-reductions[year])
    elif year>2035:
        # linear to 80% by 2050
        return base*(1 - (0.14 + (year-2035)*(0.8-0.14)/(2050-2035)))
    else:
        return base

# === PLOT FORECAST ===
years_line = [2020] + list(range(2025,2051,5))
target_vals = [91.16] + [get_target_ghg_intensity(y) for y in years_line[1:]]
fig,ax = plt.subplots(figsize=(8,4))
ax.plot(years_line,target_vals,marker='o',linestyle='--')
ax.fill_between(years_line,target_vals,alpha=0.2)
ax.set_title('GHG Target Forecast (2020–2050)')
ax.set_xlabel('Year')
ax.set_ylabel('gCO2eq/MJ')
ax.grid(True)
st.pyplot(fig)

# === SIDEBAR INPUTS ===
st.sidebar.header('Fuel Input')
fuel_defaults = pd.DataFrame(default_fuels)
selected_fuels = []
for i in range(1,4):
    name = st.sidebar.selectbox(f'Fuel {i}', ['None']+list(fuel_defaults.name), key=i)
    if name!='None':
        mass = st.sidebar.number_input(f'{name} (MT)', min_value=0.0, step=100.0, key=f'mass{i}')
        if mass>0:
            entry = fuel_defaults[fuel_defaults.name==name].iloc[0]
            selected_fuels.append({'name':name,'mass_mt':mass,'lcv':entry.lcv_mj_per_g,'ef':entry.wtw_gco2_per_mj})

st.sidebar.markdown('---')
\
# Scope and Options
ghg_scope = st.sidebar.radio('GHG Scope',['CO2 only','Full'],index=0)
pooling = st.sidebar.checkbox('Enable pooling',value=False)

# === CALCULATIONS ===
total_energy=0.0
total_emissions=0.0
fuel_rows=[]
for fuel in selected_fuels:
    mass_g = fuel['mass_mt']*1e6
    energy = mass_g * fuel['lcv']
    if ghg_scope=='CO2 only':
        ttw_per_g = 3.114
        ef_dyn = ttw_per_g/fuel['lcv'] + (fuel['ef']-((3.114+0.00005*25+0.00018*298)/fuel['lcv']))
        emissions = energy*ef_dyn
    else:
        emissions = energy * fuel['ef']
    total_energy+=energy
    total_emissions+=emissions
    fuel_rows.append({'Fuel':fuel['name'],'Energy (MJ)':energy,'Emissions (gCO2eq)':emissions})

balance = total_energy*(get_target_ghg_intensity(2025)-total_emissions/total_energy)
penalty = abs(balance)/1000*0.64 if balance<0 else 0.0

# === OUTPUT ===
st.subheader('Fuel Details')
st.dataframe(pd.DataFrame(fuel_rows))
st.subheader('Summary')
st.write(f'Total Energy: {total_energy:,.0f} MJ')
st.write(f'GHG Intensity: {total_emissions/total_energy:.2f} gCO2eq/MJ')
st.write(f'Target: {get_target_ghg_intensity(2025):.2f} gCO2eq/MJ')
st.write(f'Penalty: €{penalty:,.2f}')

if penalty==0 and pooling:
    savings = balance/1000*2.4
    st.success(f'Pooling savings: €{savings:,.2f}')
else:
    st.info('Enter values to see results.')
