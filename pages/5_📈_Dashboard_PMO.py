import streamlit as st
import pandas as pd
import plotly.express as px
from phase_model import get_timeline_data, get_main_risk
import datetime

st.title("📈 Dashboard PMO")

# Get project data
timeline_df = get_timeline_data()

# Calculate metrics
# Get the latest data point for each phase's health
latest_health = {}
for phase in ['UAT', 'Migration', 'E2E', 'Training', 'PRO', 'Hypercare']:
    health_col = f'{phase}_health'
    if health_col in timeline_df.columns:
        latest_health[phase] = timeline_df[health_col].iloc[-1] * 100

health_score = sum(latest_health.values()) / len(latest_health) if latest_health else 0
quality_score = timeline_df['total_quality'].iloc[-1] if 'total_quality' in timeline_df.columns else 0
end_date = pd.to_datetime(timeline_df.index[-1])
end_date_str = end_date.strftime('%Y-%m-%d') if not pd.isna(end_date) else 'N/A'
budget_deviation = -5.2  # Example value, should be calculated from actual data
main_risk = get_main_risk(timeline_df)

# Create project summary table
project_data = {
    'Proyecto': ['Modelo GoLive'],
    'Health Score': [f"{health_score:.1f}%"],
    'Calidad Estimada (Go-Live)': [f"{quality_score:.1f}%"],
    'Fecha Fin Estimada': [end_date_str],
    'Desviación Presupuesto': [f"{budget_deviation:.1f}%"],
    'Riesgo Clave': [main_risk]
}

df_summary = pd.DataFrame(project_data)
st.dataframe(df_summary, use_container_width=True)

# Create two columns for charts
col1, col2 = st.columns(2)

# Health Score Bar Chart
with col1:
    health_data = pd.DataFrame({
        'Fase': list(latest_health.keys()),
        'Health Score': list(latest_health.values())
    })
    
    fig_health = px.bar(
        health_data,
        x='Fase',
        y='Health Score',
        title='Health Score por Fase',
        labels={'Health Score': 'Health Score (%)', 'Fase': 'Fase'}
    )
    st.plotly_chart(fig_health, use_container_width=True)

# Bubble Chart
with col2:
    # Create bubble chart data
    bubble_data = pd.DataFrame({
        'Fase': list(latest_health.keys()),
        'Fecha Fin': [end_date] * len(latest_health),
        'Calidad': [quality_score] * len(latest_health),
        'Health': list(latest_health.values())
    })
    
    fig_bubble = px.scatter(
        bubble_data,
        x='Fecha Fin',
        y='Calidad',
        size='Health',
        hover_data=['Fase'],
        title='Fases por Fecha, Calidad y Health Score',
        labels={
            'Fecha Fin': 'Fecha de Finalización',
            'Calidad': 'Calidad Estimada (%)',
            'Health': 'Health Score'
        }
    )
    st.plotly_chart(fig_bubble, use_container_width=True)

# Add some explanatory text
st.markdown("""
### Leyenda
- **Health Score**: Indicador general de salud del proyecto
- **Calidad Estimada**: Predicción de calidad al momento del Go-Live
- **Desviación Presupuesto**: Porcentaje de desviación respecto al presupuesto planificado
- **Riesgo Clave**: Principal factor de riesgo identificado
""") 