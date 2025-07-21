import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from simulations import run_holistic_monte_carlo, calculate_confidence_intervals
from styles import COLORS

st.set_page_config(page_title="Simulaciones Avanzadas", layout="wide")

# Initialize session state variables
if 'compare_scenarios' not in st.session_state:
    st.session_state.compare_scenarios = []
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = {}

def format_currency(value):
    """Format currency values in euros with thousands separator"""
    return f"€{value:,.2f}"

def format_percentage(value):
    """Format percentage values"""
    return f"{value:.1f}%"

def format_days(value):
    """Format number of days"""
    return f"{int(value)} días"

def create_3d_scatter(results_df):
    """Create 3D scatter plot of simulation results"""
    fig = go.Figure(data=[go.Scatter3d(
        x=results_df['sim_quality'],
        y=results_df['sim_duration_days'],
        z=results_df['sim_cost'],
        mode='markers',
        marker=dict(
            size=4,
            color=results_df['sim_quality'],
            colorscale='Viridis',
            opacity=0.8
        )
    )])
    
    fig.update_layout(
        title="Distribución 3D de Resultados de Simulación",
        scene=dict(
            xaxis_title="Calidad (%)",
            yaxis_title="Duración (días)",
            zaxis_title="Coste (€)"
        ),
        width=800,
        height=800
    )
    
    return fig

def main():
    st.title("🔬 Simulaciones Avanzadas Monte Carlo")
    
    st.markdown("""
    Esta página permite realizar simulaciones Monte Carlo holísticas que consideran simultáneamente:
    - Calidad del proyecto
    - Duración total
    - Coste final
    
    La simulación utiliza una distribución PERT para modelar la variabilidad en la duración de las fases,
    y considera la interdependencia entre estas variables.
    """)
    
    # Simulation parameters
    with st.expander("⚙️ Parámetros de Simulación", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            n_simulations = st.number_input("Número de Simulaciones", 
                                          min_value=1000, 
                                          max_value=10000, 
                                          value=5000, 
                                          step=1000)
            
        with col2:
            base_monthly_cost = st.number_input("Coste Mensual Base (€)", 
                                              min_value=50000, 
                                              max_value=500000, 
                                              value=100000, 
                                              step=10000)
    
    # Run simulation button
    if st.button("🚀 Ejecutar Simulación Holística", type="primary"):
        with st.spinner("Ejecutando simulación Monte Carlo..."):
            # Get current scenario windows and risk values from session state
            scenario_windows = st.session_state.get('scenario_windows', {})
            risk_values = st.session_state.get('risk_values', {})
            
            if not scenario_windows or not risk_values:
                st.error("Por favor, configura primero las fechas y riesgos de las fases en la página principal.")
                return
            
            # Run simulation
            results_df = run_holistic_monte_carlo(
                scenario_windows=scenario_windows,
                risk_values=risk_values,
                n_simulations=n_simulations,
                base_monthly_cost=base_monthly_cost
            )
            
            # Calculate metrics
            metrics = calculate_confidence_intervals(results_df)
            
            # Display metrics in columns
            st.subheader("📊 Resultados de la Simulación")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Calidad Media Esperada",
                    format_percentage(metrics['sim_quality']['mean']),
                    delta=f"±{metrics['sim_quality']['std']:.1f}%"
                )
                st.caption(f"P10-P90: {format_percentage(metrics['sim_quality']['p10'])} - {format_percentage(metrics['sim_quality']['p90'])}")
                
            with col2:
                st.metric(
                    "Duración Media Esperada",
                    format_days(metrics['sim_duration_days']['mean']),
                    delta=f"±{int(metrics['sim_duration_days']['std'])} días"
                )
                st.caption(f"P10-P90: {format_days(metrics['sim_duration_days']['p10'])} - {format_days(metrics['sim_duration_days']['p90'])}")
                
            with col3:
                st.metric(
                    "Coste Medio Esperado",
                    format_currency(metrics['sim_cost']['mean']),
                    delta=f"±{format_currency(metrics['sim_cost']['std'])}"
                )
                st.caption(f"P10-P90: {format_currency(metrics['sim_cost']['p10'])} - {format_currency(metrics['sim_cost']['p90'])}")
            
            # Create and display 3D scatter plot
            st.subheader("🎯 Visualización 3D de Resultados")
            fig_3d = create_3d_scatter(results_df)
            st.plotly_chart(fig_3d, use_container_width=True)
            
            # Display detailed probability analysis
            st.subheader("📈 Análisis de Probabilidades")
            
            # Calculate probability of meeting specific targets
            quality_target = 90
            duration_target = 150
            cost_target = 2200000
            
            prob_quality = (results_df['sim_quality'] >= quality_target).mean() * 100
            prob_duration = (results_df['sim_duration_days'] <= duration_target).mean() * 100
            prob_cost = (results_df['sim_cost'] <= cost_target).mean() * 100
            
            # Combined probability
            prob_all = ((results_df['sim_quality'] >= quality_target) & 
                       (results_df['sim_duration_days'] <= duration_target) & 
                       (results_df['sim_cost'] <= cost_target)).mean() * 100
            
            st.write(f"""
            Probabilidades de éxito según diferentes criterios:
            - Calidad ≥ {quality_target}%: {prob_quality:.1f}%
            - Duración ≤ {duration_target} días: {prob_duration:.1f}%
            - Coste ≤ {format_currency(cost_target)}: {prob_cost:.1f}%
            - **Probabilidad de cumplir TODOS los criterios: {prob_all:.1f}%**
            """)

            # Save current scenario results if needed
            if st.button("💾 Guardar Escenario Actual"):
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                scenario_name = f"Escenario_{timestamp}"
                st.session_state.scenarios[scenario_name] = {
                    'windows': scenario_windows.copy(),
                    'risks': risk_values.copy(),
                    'results': results_df.copy(),
                    'metrics': metrics.copy()
                }
                st.session_state.compare_scenarios.append(scenario_name)
                st.success(f"Escenario guardado como: {scenario_name}")

if __name__ == "__main__":
    main() 