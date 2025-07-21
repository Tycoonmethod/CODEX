import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import json
from scipy import stats
from translations import TEXT, LANGUAGES
from styles import COLORS, inject_custom_css, card, metric, phase_bar, PLOT_LAYOUT

# Inject custom CSS
inject_custom_css()


# --- Helper Functions ---
def formatted_money_input(label, value, key, min_value=0.0):
    """Helper function to format monetary inputs with thousands separators and € symbol"""
    # Format display
    formatted_value = f"{value:,.2f}€" if value is not None else "0.00€"
    # Use text_input for custom formatting
    input_str = st.text_input(label, value=formatted_value, key=f"{key}_str")
    try:
        # Parse: remove commas and €
        clean_str = input_str.replace(",", "").replace("€", "").strip()
        new_value = float(clean_str) if clean_str else 0.0
        if new_value < min_value:
            new_value = min_value
        st.session_state[key] = new_value
        return new_value
    except ValueError:
        # If invalid, keep old value
        return value


def format_money(value):
    """Format monetary values with thousands separators and € symbol"""
    return f"{value:,.0f}€"


# --- Teams Configuration ---
teams = {
    "EDP": ["EDP Central Team", "EDP DGU Central Team"],
    "NTT DATA": [
        "NTT DATA Transformation Office",
        "NTT DATA Development Team",
        "NTT DATA Functional Team",
    ],
    "Minsait": ["Minsait Data Team"],
}


# --- State Initialization (Robust, In-Page) ---
def initialize_state():
    defaults = {
        "lang": "es",
        "project_name": "Proyecto Go-Live 2025",
        "sponsor": "CEO",
        "budget_total": 2000000,
        "budget_used": 75,
        "team_size": 25,
        "uat_days": 23,
        "migration_days": 23,
        "e2e_days": 30,
        "training_days": 31,
        "pro_env_days": 15,
        "golive_days": 6,
        "user_availability": 85,  # Add missing key
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Calculate total project days
    total_days = (
        st.session_state.uat_days
        + st.session_state.migration_days
        + st.session_state.e2e_days
        + st.session_state.training_days
        + st.session_state.golive_days
        + st.session_state.pro_env_days
        + 30
    )  # +30 for hypercare

    # Initialize team costs, budgets, and durations
    if "costs" not in st.session_state:
        st.session_state.costs = {
            team: 0.0 for company in teams for team in teams[company]
        }
    if "budgets" not in st.session_state:
        st.session_state.budgets = {
            team: 0.0 for company in teams for team in teams[company]
        }
    if "durations" not in st.session_state:
        st.session_state.durations = {
            team: total_days for company in teams for team in teams[company]
        }
    if "selected_company" not in st.session_state:
        st.session_state.selected_company = "EDP"


initialize_state()
lang = st.session_state.lang


# --- MODELO Y FUNCIONES AUXILIARES (sin cambios) ---
def quality_model_econometric(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
):
    migration_factor = migration_pct / 100
    if migration_pct < 100:
        bloqueo_factor = migration_factor * 0.6
        e2e_pct *= bloqueo_factor
        training_pct *= bloqueo_factor
    valor_original = (
        1.00
        + 0.25 * (uat_pct / 100)
        + 0.40 * (migration_pct / 100)
        + 0.20 * (e2e_pct / 100)
        + 0.15 * (training_pct / 100)
        + 0.10 * (resources_pct / 100)
        + 0.10 * (hypercare_pct / 100)
    )
    return min(max((valor_original / 2.20) * 100, 0), 100)


# --- Funciones auxiliares (sin cambios) ---
def calcular_riesgo_proyecto(
    migration_days, e2e_days, training_days, team_size, budget_pct
):
    riesgo_base = 0.1
    if migration_days > 23:
        riesgo_base += (migration_days - 23) * 0.02
    if team_size < 10:
        riesgo_base += 0.15
    if budget_pct < 80:
        riesgo_base += 0.20
    return min(riesgo_base, 1.0)


def simulacion_monte_carlo(scenarios, n_simulations=1000):
    resultados = []
    for _ in range(n_simulations):
        migration_sim = max(scenarios["Migration"] * np.random.normal(1.0, 0.15), 23)
        calidad = quality_model_econometric(100, 100, 100, 100, 100, 0)
        if migration_sim > 23:
            delay = migration_sim - 23
            eficiencia = max(0.5, 1.0 - (delay * 0.05))
            calidad = quality_model_econometric(100, 100 * eficiencia, 100, 100, 100, 0)
        resultados.append({"calidad": calidad})
    return pd.DataFrame(resultados)


# --- UI ---
st.set_page_config(page_title="Dashboard Avanzado", layout="wide")

# Create a container for the main content
main_container = st.container()

# Sidebar with collapsible configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuración del Proyecto")

    # Project configuration in an expander
    with st.expander("📊 Parámetros Principales", expanded=True):
        st.text_input(
            TEXT[lang]["project_name"],
            value=st.session_state.project_name,
            key="project_name",
        )
        st.selectbox(TEXT[lang]["sponsor"], ["CEO", "CTO", "CFO", "COO"], key="sponsor")
        st.number_input(
            TEXT[lang]["budget"],
            value=st.session_state.budget_total,
            key="budget_total",
            step=50000,
        )
        st.slider(
            TEXT[lang]["budget_used"],
            0,
            150,
            value=st.session_state.budget_used,
            key="budget_used",
        )
        st.slider(
            TEXT[lang]["team_size"],
            5,
            100,
            value=st.session_state.team_size,
            key="team_size",
        )
        st.slider(
            f"Días Migration (CRÍTICA)",
            23,
            60,
            value=st.session_state.migration_days,
            key="migration_days",
        )
        st.slider(
            TEXT[lang]["user_availability"],
            50,
            100,
            value=st.session_state.user_availability,
            key="user_availability",
        )

# --- Cálculos ---
delay_migration = max(0, st.session_state.migration_days - 23)
riesgo_proyecto = calcular_riesgo_proyecto(
    st.session_state.migration_days,
    30,
    31,
    st.session_state.team_size,
    st.session_state.budget_used,
)
eficiencia_mig = max(0.5, 1.0 - (delay_migration * 0.05))
calidad_actual = quality_model_econometric(100, 100 * eficiencia_mig, 100, 100, 100, 0)
coste_estimado = st.session_state.budget_total * (st.session_state.budget_used / 100)
eficiencia_equipo = min(
    100, (st.session_state.team_size * st.session_state.user_availability) / 20
)

# Main content area with cards
with main_container:
    st.title(TEXT[lang]["page2_name"])

    # Top row with KPI cards
    col1, col2 = st.columns(2)

    with col1:
        # Project Health Card
        health_content = (
            metric(
                "Calidad del Proyecto", f"{calidad_actual:.1f}%", calidad_actual - 95.5
            )
            + metric("Riesgo Global", f"{riesgo_proyecto*100:.1f}%")
            + metric("Eficiencia del Equipo", f"{eficiencia_equipo:.0f}%")
        )
        st.markdown(
            card("🎯 Salud del Proyecto", health_content), unsafe_allow_html=True
        )

    with col2:
        # Financial Metrics Card
        financial_content = (
            metric("Coste Estimado", format_money(coste_estimado))
            + metric("Presupuesto Utilizado", f"{st.session_state.budget_used}%")
            + metric("Tamaño del Equipo", f"{st.session_state.team_size} personas")
        )
        st.markdown(
            card("💰 Métricas Financieras", financial_content), unsafe_allow_html=True
        )

    # Enhanced Cost Distribution Chart Card
    cost_content = f"""
    <div style="margin-bottom: 1rem;">
        <div style="font-size: 0.875rem; color: #ffffff; margin-bottom: 0.5rem;">Selecciona empresa para configurar costes por equipo:</div>
    </div>
    """

    # Company selector
    selected_company = st.selectbox(
        "Empresa", list(teams.keys()), key="selected_company"
    )

    # Cost inputs for selected company teams
    st.markdown(f"### Costes para {selected_company}")

    # Create columns for team cost inputs
    company_teams = teams[selected_company]
    if len(company_teams) <= 2:
        cols = st.columns(len(company_teams))
    else:
        cols = st.columns(3)

    for i, team in enumerate(company_teams):
        with cols[i % len(cols)]:
            team_key = team.replace(" ", "_").replace("-", "_")
            cost_value = formatted_money_input(
                f"Coste {team}", st.session_state.costs[team], key=f"cost_{team_key}"
            )
            st.session_state.costs[team] = cost_value

    # Calculate pie chart data
    categories = []
    values = []
    colors = []
    color_palette = [
        COLORS["baseline"],
        COLORS["scenario"],
        COLORS["phases"],
        COLORS["golive"],
        COLORS["success"],
        COLORS["warning"],
    ]

    for i, (company, company_teams) in enumerate(teams.items()):
        for j, team in enumerate(company_teams):
            if st.session_state.costs[team] > 0:
                categories.append(f"{team} ({company})")
                values.append(st.session_state.costs[team])
                colors.append(color_palette[(i * 2 + j) % len(color_palette)])

    # Show pie chart if there are costs
    if values and sum(values) > 0:
        fig_costes = px.pie(
            values=values,
            names=categories,
            title="Distribución de Costes por Equipo",
            color_discrete_sequence=colors,
        )
        fig_costes.update_layout(**PLOT_LAYOUT)
        fig_costes.update_traces(
            texttemplate="%{label}<br>%{percent:.1%}<br>(%{value:,.0f}€)",
            textposition="inside",
        )
        st.plotly_chart(fig_costes, use_container_width=True)

        # Summary metrics
        total_cost = sum(values)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                metric("Coste Total", format_money(total_cost)), unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                metric("Equipos Activos", f"{len(values)}"), unsafe_allow_html=True
            )
        with col3:
            budget_usage = (
                (total_cost / st.session_state.budget_total) * 100
                if st.session_state.budget_total > 0
                else 0
            )
            st.markdown(
                metric("Uso del Presupuesto", f"{budget_usage:.1f}%"),
                unsafe_allow_html=True,
            )
    else:
        st.info("💡 Introduce costes para los equipos para ver la distribución")

    # Historical Tracking and Forecasting Section
    st.markdown("---")
    st.subheader("📈 Seguimiento Histórico y Forecasting por Equipo")

    # Calculate total project days
    total_days = (
        st.session_state.uat_days
        + st.session_state.migration_days
        + st.session_state.e2e_days
        + st.session_state.training_days
        + st.session_state.golive_days
        + st.session_state.pro_env_days
        + 30
    )  # +30 for hypercare

    # Team tracking for all companies
    for company, company_teams in teams.items():
        if any(st.session_state.costs[team] > 0 for team in company_teams):
            st.markdown(f"#### {company}")

            for team in company_teams:
                if st.session_state.costs[team] > 0:
                    with st.expander(
                        f"📊 {team} - Tracking & Forecast", expanded=False
                    ):

                        # Budget and duration inputs
                        col1, col2 = st.columns(2)

                        with col1:
                            team_key = team.replace(" ", "_").replace("-", "_")
                            budget_value = formatted_money_input(
                                f"Budget para {team}",
                                st.session_state.budgets[team],
                                key=f"budget_{team_key}",
                            )
                            st.session_state.budgets[team] = budget_value

                        with col2:
                            duration_value = st.number_input(
                                f"Duración del contrato (días)",
                                min_value=1,
                                max_value=total_days * 2,
                                value=st.session_state.durations[team],
                                key=f"duration_{team}",
                            )
                            st.session_state.durations[team] = duration_value

                        # Calculate metrics and forecast
                        if duration_value > 0 and budget_value > 0:
                            daily_rate = budget_value / duration_value

                            # Metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(
                                    metric("Tarifa Diaria", format_money(daily_rate)),
                                    unsafe_allow_html=True,
                                )
                            with col2:
                                consumed_days = min(total_days, duration_value)
                                consumption_pct = (consumed_days / duration_value) * 100
                                st.markdown(
                                    metric(
                                        "Consumo Estimado", f"{consumption_pct:.1f}%"
                                    ),
                                    unsafe_allow_html=True,
                                )
                            with col3:
                                estimated_cost = daily_rate * consumed_days
                                st.markdown(
                                    metric(
                                        "Coste Estimado", format_money(estimated_cost)
                                    ),
                                    unsafe_allow_html=True,
                                )

                            # Linear forecast
                            forecast_days = np.arange(min(total_days, duration_value))
                            forecast_consumption = np.linspace(
                                0,
                                budget_value * (len(forecast_days) / duration_value),
                                len(forecast_days),
                            )

                            # Create forecast chart
                            fig_forecast = px.line(
                                x=forecast_days,
                                y=forecast_consumption,
                                title=f"Forecast Consumo {team} hasta Go-Live + Hypercare",
                                labels={
                                    "x": "Días de Proyecto",
                                    "y": "Consumo Acumulado (€)",
                                },
                            )
                            fig_forecast.update_layout(
                                yaxis_title="Consumo Acumulado (€)", **PLOT_LAYOUT
                            )
                            fig_forecast.update_traces(
                                line_color=COLORS["baseline"],
                                line_width=3,
                                hovertemplate="Día %{x}: %{y:,.2f}€<extra></extra>",
                            )

                            # Add current day marker (assuming day 50 of project)
                            current_day = 50
                            if current_day < len(forecast_days):
                                fig_forecast.add_vline(
                                    x=current_day,
                                    line_dash="dash",
                                    line_color=COLORS["warning"],
                                    annotation_text="Hoy",
                                )

                            st.plotly_chart(fig_forecast, use_container_width=True)

                            # Risk indicators
                            if consumption_pct > 80:
                                st.warning(
                                    f"⚠️ {team}: Alto consumo del presupuesto ({consumption_pct:.1f}%)"
                                )
                            elif consumption_pct > 60:
                                st.info(
                                    f"ℹ️ {team}: Consumo moderado del presupuesto ({consumption_pct:.1f}%)"
                                )
                        else:
                            st.info(
                                "💡 Introduce budget y duración para ver el forecast"
                            )

    # ROI Analysis Card
    roi_content = "<div style='margin-bottom: 1rem;'>"
    beneficio_anual = formatted_money_input(
        TEXT[lang]["roi_benefit"],
        st.session_state.get("beneficio_anual", 5000000),
        key="beneficio_anual",
    )
    roi = (
        (beneficio_anual - st.session_state.budget_total)
        / st.session_state.budget_total
    ) * 100
    payback = (
        (st.session_state.budget_total / beneficio_anual) * 12
        if beneficio_anual > 0
        else 0
    )
    roi_content += metric("ROI a 1 año", f"{roi:.1f}%")
    roi_content += metric("Payback", f"{payback:.1f} meses")
    roi_content += "</div>"
    st.markdown(card("📈 Análisis ROI", roi_content), unsafe_allow_html=True)

    # Monte Carlo Simulation - Python implementation with Plotly histogram
    st.subheader("🎲 Simulación Monte Carlo")

    def monte_carlo_simulation(n_simulations=10000):
        """Execute Monte Carlo simulation with econometric model"""
        results = []

        for _ in range(n_simulations):
            # Migration delay factor
            migration_delay = max(0, st.session_state.migration_days - 23)
            migration_efficiency = max(0.5, 1.0 - (migration_delay * 0.05))

            # Add random variability (±15% for migration)
            migration_factor = max(
                0.3, migration_efficiency * np.random.uniform(0.85, 1.15)
            )

            # Econometric model with Migration as critical phase (0.40 weight)
            uat_pct = 1.0
            migration_pct = migration_factor
            e2e_pct = migration_pct if migration_pct >= 1.0 else migration_pct * 0.6
            training_pct = (
                migration_pct if migration_pct >= 1.0 else migration_pct * 0.6
            )
            resources_pct = min(1.0, st.session_state.team_size / 25)
            hypercare_pct = 0.0

            valor_original = (
                1.00
                + 0.25 * uat_pct
                + 0.40 * migration_pct  # Migration is critical with double weight
                + 0.20 * e2e_pct
                + 0.15 * training_pct
                + 0.10 * resources_pct
                + 0.10 * hypercare_pct
            )

            calidad = min(max((valor_original / 2.20) * 100, 0), 100)

            # Budget risk factor
            if st.session_state.budget_used > 100:
                calidad *= 0.95

            # Add realistic noise (±5%)
            noise = np.random.uniform(-5, 5)
            calidad += noise

            results.append(max(0, min(100, calidad)))

        return np.array(results)

    # Monte Carlo execution button
    if st.button("🎲 Ejecutar Simulación (10.000 iteraciones)"):
        with st.spinner("Calculando..."):
            # Run Monte Carlo simulation
            results = monte_carlo_simulation(10000)

            # Calculate metrics
            mean_quality = np.mean(results)
            success_prob = (np.sum(results >= 80) / len(results)) * 100
            median = np.median(results)
            min_val = np.min(results)
            max_val = np.max(results)

            # Debug info
            st.write(
                f"Debug: {len(results)} simulaciones procesadas (media: {mean_quality:.1f}%)"
            )

            # Display metrics in columns
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown(
                    metric("Calidad Media", f"{mean_quality:.1f}%"),
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    metric("Probabilidad de Éxito", f"{success_prob:.1f}%"),
                    unsafe_allow_html=True,
                )

            with col3:
                st.markdown(metric("Mediana", f"{median:.1f}%"), unsafe_allow_html=True)

            with col4:
                st.markdown(
                    metric("Rango", f"{min_val:.1f}% - {max_val:.1f}%"),
                    unsafe_allow_html=True,
                )

            # Summary text
            st.markdown(
                f'<div style="font-size: 0.9rem; color: {COLORS["muted"]}; opacity: 0.8; margin-top: 1rem;">Umbral de éxito: 80% | Simulaciones: {len(results):,}</div>',
                unsafe_allow_html=True,
            )

            # Create histogram with enhanced error handling
            try:
                fig = px.histogram(
                    results,
                    nbins=50,
                    title="Distribución de Calidad Go-Live (Monte Carlo)",
                    color_discrete_sequence=[COLORS["baseline"]],
                    labels={"value": "Calidad (%)", "count": "Frecuencia"},
                )
                fig.update_layout(height=400, **PLOT_LAYOUT)
                fig.update_traces(marker_line_width=0, opacity=0.8)
                st.plotly_chart(fig, use_container_width=True, theme=None)

            except Exception as e:
                st.error(f"Error al generar histograma Plotly: {e}")

                # Fallback: Create histogram using st.bar_chart with numpy
                st.subheader("Histograma (Fallback)")
                hist, bins = np.histogram(results, bins=30)
                bin_centers = (bins[:-1] + bins[1:]) / 2

                # Create DataFrame for st.bar_chart
                hist_df = pd.DataFrame({"Calidad (%)": bin_centers, "Frecuencia": hist})
                hist_df = hist_df.set_index("Calidad (%)")

                st.bar_chart(hist_df, height=400)

    # Alerts Card
    if delay_migration > 0:
        alert_content = f"""
        <div style="color: {COLORS['danger']}; font-weight: bold;">
            🔴 CRÍTICO: Migration con {delay_migration} días de delay
        </div>
        """
        st.markdown(card("⚠️ Alertas", alert_content), unsafe_allow_html=True)
