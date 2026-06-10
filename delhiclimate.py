import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

# --- CONFIGURATION ---
st.set_page_config(page_title="Delhi Heat Monitor: Actual vs Projected", layout="wide")

# --- 1. DATA LOADING & ROBUST CLEANING ---
@st.cache_data
def load_data(temp_path, lulc_path):
    df = pd.read_csv(temp_path, low_memory=False)
    def parse_date(val):
        if pd.isna(val): return pd.NaT
        for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try: return pd.to_datetime(str(val).strip(), format=fmt)
            except: continue
        return pd.to_datetime(val, errors='coerce')

    df['Date'] = df['Date'].apply(parse_date)
    df['Temp Max'] = pd.to_numeric(df['Temp Max'], errors='coerce')
    df['Temp Min'] = pd.to_numeric(df['Temp Min'], errors='coerce')
    df = df.dropna(subset=['Date', 'Temp Max', 'Temp Min']).sort_values('Date')
    
    df_lulc = pd.read_csv(lulc_path)
    df_lulc = df_lulc.sort_values('Year End')
    df_lulc['Built-up'] = pd.to_numeric(df_lulc['Built-up'], errors='coerce').interpolate()
    
    return df, df_lulc

# --- 2. THE PROJECTION & SMOOTHING ENGINE (MPD-2041 INTEGRATED) ---
@st.cache_resource
def generate_unified_model(df_temp, df_lulc):
    last_actual_date = df_temp['Date'].max()
    current_year = last_actual_date.year
    
    # 1. Calculate UHI Sensitivity (Degrees rise per 1 L ha of urbanization)
    yearly_actuals = df_temp.groupby(df_temp['Date'].dt.year).agg({'Temp Max': 'mean', 'Temp Min': 'mean'}).reset_index()
    merged = pd.merge(yearly_actuals, df_lulc, left_on='Date', right_on='Year End')
    uhi_model = LinearRegression().fit(merged[['Built-up']], merged['Temp Min'])
    uhi_factor = uhi_model.coef_[0]

    # 2. MPD-2041 Growth Parameters
    # Current (2025): 0.84 L ha | Target Expansion: 0.57 L ha by 2041
    current_built_up = df_lulc[df_lulc['Year End'] == 2025]['Built-up'].values[0]
    expansion_target = 0.57  # 57,000 hectares = 0.57 Lakh Hectares
    years_to_2041 = 2041 - 2025
    annual_growth_rate = expansion_target / years_to_2041 # ~0.035 L ha per year
    max_saturation = 1.41 # (0.84 + 0.57) - Cap based on MPD 2041 goals

    # 3. SEASONAL BASELINE (Last 5 Years)
    recent = df_temp[df_temp['Date'] >= (last_actual_date - timedelta(days=1825))].copy()
    recent['DOY'] = recent['Date'].dt.dayofyear
    clim = recent.groupby('DOY')[['Temp Max', 'Temp Min']].mean()

    # 4. GENERATE FUTURE (Tomorrow to 2100)
    future_range = pd.date_range(start=last_actual_date + timedelta(days=1), end='2100-12-31', freq='D')
    proj_list = []
    
    for dt in future_range:
        doy = min(dt.timetuple().tm_yday, 365)
        years_out = dt.year - current_year
        
        # Calculate policy-driven Built-up for the current year
        if dt.year <= 2041:
            built_up_at_year = current_built_up + ((dt.year - 2025) * annual_growth_rate)
        else:
            built_up_at_year = max_saturation # Post-2041 stabilization
            
        # Total Warming = (Global IPCC Trend) + (Local Urbanization Effect)
        # Local effect is (Change in Built-up since 2025) * UHI Sensitivity
        urban_warming = (built_up_at_year - current_built_up) * uhi_factor
        global_warming = years_out * 0.022
        
        warming = global_warming + urban_warming
        
        proj_list.append({
            'Date': dt, 
            'Temp Max': clim.loc[doy, 'Temp Max'] + warming,
            'Temp Min': clim.loc[doy, 'Temp Min'] + warming, 
            'Year': dt.year
        })
    
    df_proj = pd.DataFrame(proj_list)

    # --- 5. SMOOTH TREND BRIDGE (2026/2027) ---
    actual_2026 = df_temp[df_temp['Date'].dt.year == current_year]
    proj_2026 = df_proj[df_proj['Date'].dt.year == current_year]
    avg_max_2026 = pd.concat([actual_2026['Temp Max'], proj_2026['Temp Max']]).mean()
    avg_min_2026 = pd.concat([actual_2026['Temp Min'], proj_2026['Temp Min']]).mean()

    yearly_h = yearly_actuals[yearly_actuals['Date'] < current_year].copy()
    row_2026 = pd.DataFrame({'Date': [current_year], 'Temp Max': [avg_max_2026], 'Temp Min': [avg_min_2026]})
    yearly_h = pd.concat([yearly_h, row_2026]).sort_values('Date')
    
    yearly_p = df_proj.groupby('Year').agg({'Temp Max': 'mean', 'Temp Min': 'mean'}).reset_index()
    yearly_p = yearly_p[yearly_p['Year'] > current_year]

    return df_temp, df_proj, yearly_h, yearly_p, last_actual_date

# --- EXECUTION ---
try:
    df_actual, df_proj, yearly_h, yearly_p, cutoff = generate_unified_model(*load_data('DelhiHistoricData19702024.csv', 'DelhiLULC.csv'))

    # --- TOP LEVEL METRICS ---
    st.title("🌡️ Delhi Daily Temperature: Max vs. Min")
    
    hottest_rec_row = df_actual.loc[df_actual['Temp Max'].idxmax()]
    hottest_proj_row = df_proj.loc[df_proj['Temp Max'].idxmax()]
    
    yearly_h['YearlyAvg'] = (yearly_h['Temp Max'] + yearly_h['Temp Min']) / 2
    hottest_year_val = yearly_h.loc[yearly_h['YearlyAvg'].idxmax()]

    m1, m2, m3 = st.columns(3)
    
    # Custom CSS to hide delta arrows but keep the "bubble" look
    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric("Hottest Recorded", f"{hottest_rec_row['Temp Max']:.1f}°C")
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.8rem;'>{hottest_rec_row['Date'].strftime('%d %b %Y')}</p>", unsafe_allow_html=True)

    with m2:
        st.metric("Projected Peak (2100)", f"{hottest_proj_row['Temp Max']:.1f}°C")
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.8rem;'>{hottest_proj_row['Date'].strftime('%d %b %Y')}</p>", unsafe_allow_html=True)

    with m3:
        st.metric("Hottest Year (Avg)", int(hottest_year_val['Date']))
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.8rem;'>{hottest_year_val['YearlyAvg']:.1f}°C Avg</p>", unsafe_allow_html=True)

    st.markdown("---")

    # --- CHART 1: YEARLY TREND ---
    st.subheader("📊 Yearly Temperature Trend (1951 - 2100)")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=yearly_h['Date'], y=yearly_h['Temp Max'], name="Historic Max", line=dict(color="#1f77b4")))
    fig1.add_trace(go.Scatter(x=yearly_h['Date'], y=yearly_h['Temp Min'], name="Historic Min", line=dict(color="#17becf")))
    
    # Start projection line from the last point of historic to ensure connectivity
    proj_x = [yearly_h['Date'].iloc[-1]] + yearly_p['Year'].tolist()
    proj_max_y = [yearly_h['Temp Max'].iloc[-1]] + yearly_p['Temp Max'].tolist()
    proj_min_y = [yearly_h['Temp Min'].iloc[-1]] + yearly_p['Temp Min'].tolist()
    
    fig1.add_trace(go.Scatter(x=proj_x, y=proj_max_y, name="Projected Max", line=dict(color="#d62728", dash="dot")))
    fig1.add_trace(go.Scatter(x=proj_x, y=proj_min_y, name="Projected Min", line=dict(color="#ff7f0e", dash="dot")))
    
    fig1.update_layout(height=400, template="plotly_white", hovermode="x unified", margin=dict(t=10))
    st.plotly_chart(fig1, use_container_width=True)

    # --- CHART 2: SEASONAL VIEW (DAILY) ---
    st.subheader("📅 Seasonal Daily View")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_actual['Date'], y=df_actual['Temp Max'], name='Actual Max', line=dict(color='#1f77b4', width=1.5)))
    fig2.add_trace(go.Scatter(x=df_actual['Date'], y=df_actual['Temp Min'], name='Actual Min', line=dict(color='#17becf', width=1.5)))
    fig2.add_trace(go.Scatter(x=df_proj['Date'], y=df_proj['Temp Max'], name='Projected Max', line=dict(color='#d62728', width=1, dash='dot'), opacity=0.6))
    fig2.add_trace(go.Scatter(x=df_proj['Date'], y=df_proj['Temp Min'], name='Projected Min', line=dict(color='#ff7f0e', width=1, dash='dot'), opacity=0.6))

    fig2.add_vline(x=cutoff, line_dash="dash", line_color="green")
    fig2.update_layout(
        height=600, template="plotly_white", hovermode="x unified",
        xaxis=dict(rangeslider=dict(visible=True), type="date", range=[cutoff - timedelta(days=180), cutoff + timedelta(days=365)]),
        yaxis_title="Temperature (°C)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")