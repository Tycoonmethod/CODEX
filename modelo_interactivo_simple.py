import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, date, time as dt_time, timedelta
import traceback
from delay_impact_factors import get_delay_impact_factor

# Inicializar fechas por defecto
start_date = datetime.now()
if "scenario_windows" not in st.session_state:
    st.session_state.scenario_windows = {
        'UAT': {'start': start_date, 'end': start_date + timedelta(days=15)},
        'Migration': {'start': start_date + timedelta(days=15), 'end': start_date + timedelta(days=30)},
        'E2E': {'start': start_date + timedelta(days=30), 'end': start_date + timedelta(days=45)},
        'Training': {'start': start_date + timedelta(days=45), 'end': start_date + timedelta(days=60)},
        'PRO': {'start': start_date + timedelta(days=45), 'end': start_date + timedelta(days=60)},
        'Hypercare': {'start': start_date + timedelta(days=60), 'end': start_date + timedelta(days=75)}
    }

if "baseline_windows" not in st.session_state:
    st.session_state.baseline_windows = st.session_state.scenario_windows.copy()

def get_delay_impacts(fase, delay_days):
    """Calcula los impactos de delay para una fase específica"""
    if delay_days > 0:
        # Impacto marginal (solo esta fase)
        impact_factor = get_delay_impact_factor(fase)
        marginal_impact = delay_days * (impact_factor / 100)
        
        # Calcular fases afectadas
        affected_phases = []
        if fase == "UAT":
            affected_phases = ["Migration", "E2E", "PRO", "Training", "Hypercare"]
        elif fase == "Migration":
            affected_phases = ["E2E", "PRO", "Training", "Hypercare"]
        elif fase == "E2E":
            affected_phases = ["PRO", "Training", "Hypercare"]
        elif fase in ["PRO", "Training"]:
            affected_phases = ["Hypercare"]
        
        return {
            "impact_factor": impact_factor,
            "marginal_impact": marginal_impact,
            "affected_phases": affected_phases
        }
    return None

def main():
    # Título principal
    st.title("📊 Modelo Interactivo")

    # Descripción
    st.markdown("""
    Analiza la evolución de la calidad y el impacto de los delays.
    """)

    # Tabla de Impacto de Delays
    st.markdown("### 📊 Impacto de Delays en la Calidad")
    
    # Calcular impactos de delays actuales
    delay_impacts = []
    accumulated_impact = 0
    
    for fase in ["UAT", "Migration", "E2E", "Training", "PRO", "Hypercare"]:
        if fase == "PRO":
            # ✅ PRO: usar delay directo del slider
            end_real = st.session_state.scenario_windows["PRO"]["end"]
            end_base = st.session_state.baseline_windows["PRO"]["end"]
            delay = max(0, (end_real - end_base).days)
        else:
            end_real = st.session_state.scenario_windows[fase]["end"]
            end_base = st.session_state.baseline_windows[fase]["end"]
            delay = max(0, (end_real - end_base).days)
            
        if delay > 0:
            # Impacto marginal (solo esta fase)
            impact_factor = get_delay_impact_factor(fase)
            marginal_impact = delay * (impact_factor / 100)
            
            # Impacto acumulado
            accumulated_impact += marginal_impact
            
            # Calcular fases afectadas
            affected_phases = []
            if fase == "UAT":
                affected_phases = ["Migration", "E2E", "PRO", "Training", "Hypercare"]
            elif fase == "Migration":
                affected_phases = ["E2E", "PRO", "Training", "Hypercare"]
            elif fase == "E2E":
                affected_phases = ["PRO", "Training", "Hypercare"]
            elif fase in ["PRO", "Training"]:
                affected_phases = ["Hypercare"]
            
            delay_impacts.append({
                "Fase": fase,
                "Días de Delay": delay,
                "Impacto por Día": f"{impact_factor:.2f}%",
                "Impacto Marginal": f"{(marginal_impact * 100):.2f}%",
                "Impacto Acumulado": f"{(accumulated_impact * 100):.2f}%",
                "Fases Afectadas": ", ".join(affected_phases)
            })

    # Mostrar la tabla de impactos
    if delay_impacts:
        df_impacts = pd.DataFrame(delay_impacts)
        st.dataframe(df_impacts, use_container_width=True)
    else:
        st.info("No hay delays en ninguna fase del proyecto.")

if __name__ == "__main__":
    main() 