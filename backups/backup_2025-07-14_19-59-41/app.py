import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
from translations import LANGUAGES, TEXT
from styles import inject_custom_css, card, metric, COLORS, PLOT_LAYOUT

# Inject custom CSS
inject_custom_css()


# --- State Initialization ---
def initialize_state():
    # Diccionario de valores por defecto
    defaults = {
        "lang": "es",
        "project_name": "Proyecto Go-Live 2025",
        "sponsor": "CEO",
        "criticism": "Alta",
        "budget_total": 2000000,
        "budget_used": 75,
        "team_size": 25,
        "consultants": 5,
        "user_availability": 80,
        "uat_days": 23,
        "migration_days": 23,
        "e2e_days": 30,
        "training_days": 31,
        "golive_days": 6,
        "pro_env_days": 15,
        "tech_risk": 30,
        "business_risk": 25,
        "scope_changes": 10,
        "risks": [
            {
                "name": "Retraso crítico en Migración",
                "impact": 5,
                "probability": 40,
                "owner": "Jefe de Proyecto",
            },
            {
                "name": "Baja calidad de datos de origen",
                "impact": 4,
                "probability": 60,
                "owner": "Equipo de Datos",
            },
        ],
        "selected_page": "home",
    }
    # Inicializar solo si no existe
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()

# --- Page Configuration ---
st.set_page_config(
    page_title=TEXT[st.session_state.lang]["app_title"],
    page_icon="🚀",
    layout="wide",
)

# --- Language Selector ---
_, col2 = st.columns([0.85, 0.15])
with col2:
    selected_lang_display = st.selectbox(
        " ", list(LANGUAGES.keys()), label_visibility="collapsed"
    )
    st.session_state.lang = LANGUAGES[selected_lang_display]

# --- Sidebar Navigation ---
lang = st.session_state.lang

with st.sidebar:
    st.markdown("### 📊 Navegación")

    # Page selector
    page_options = {
        "🏠 Inicio": "home",
        TEXT[lang]["page1_name"]: "page1",
        TEXT[lang]["page2_name"]: "page2",
        TEXT[lang]["page3_name"]: "page3",
    }

    selected_page_display = st.selectbox(
        "Seleccionar página:",
        list(page_options.keys()),
        index=list(page_options.values()).index(st.session_state.selected_page),
    )
    st.session_state.selected_page = page_options[selected_page_display]

    st.markdown("---")

    # Configuration section
    st.markdown("### ⚙️ Configuración")
    with st.expander("📊 Parámetros del Proyecto", expanded=False):
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
            TEXT[lang]["user_availability"],
            50,
            100,
            value=st.session_state.user_availability,
            key="user_availability",
        )

    with st.expander("⚙️ Configuración de Fases", expanded=False):
        st.slider("Días UAT", 15, 45, value=st.session_state.uat_days, key="uat_days")
        st.slider(
            "Días Migration (CRÍTICA)",
            20,
            60,
            value=st.session_state.migration_days,
            key="migration_days",
        )
        st.slider("Días E2E", 20, 50, value=st.session_state.e2e_days, key="e2e_days")
        st.slider(
            "Días Training",
            20,
            50,
            value=st.session_state.training_days,
            key="training_days",
        )
        st.slider(
            "Días Go-Live", 3, 15, value=st.session_state.golive_days, key="golive_days"
        )


# --- Monte Carlo Simulation Function ---
def run_monte_carlo_simulation(iterations=10000, threshold=80):
    """Run Monte Carlo simulation with proper econometric model"""
    results = []

    for _ in range(iterations):
        # Derive percentages as decimals (0-1)
        uat_pct = min(1.0, st.session_state.uat_days / 30)
        migration_pct = min(1.0, st.session_state.migration_days / 25)
        e2e_pct = min(1.0, st.session_state.e2e_days / 35)
        training_pct = min(1.0, st.session_state.training_days / 30)
        resources_pct = st.session_state.user_availability / 100
        hypercare_pct = min(1.0, st.session_state.golive_days / 10)

        # Adjust migration with random factor
        factor = np.random.uniform(0.85, 1.15)
        adjusted_migration = migration_pct * factor
        adjusted_migration = max(
            0.5, min(1.0, adjusted_migration)
        )  # Clamp to [0.5, 1.0]

        # Compute valor_original with econometric model
        valor_original = (
            1.0
            + 0.25 * uat_pct
            + 0.40 * adjusted_migration  # Migration is critical
            + 0.20 * e2e_pct
            + 0.15 * training_pct
            + 0.10 * resources_pct
            + 0.10 * hypercare_pct
        )

        # Calculate quality
        calidad = min(max((valor_original / 2.20) * 100, 0), 100)

        # Add noise
        calidad += np.random.uniform(-5, 5)
        calidad = max(0, min(100, calidad))

        results.append(calidad)

    return results


# --- Page Content ---
if st.session_state.selected_page == "home":
    # Home Page Content
    st.title(TEXT[lang]["welcome_title"])
    st.markdown(TEXT[lang]["welcome_message"])

    # Project Overview Card
    overview_content = f"""
    <div style="margin-bottom: 1rem;">
        {metric("Sponsor", st.session_state.sponsor)}
        {metric("Presupuesto Total", f"${st.session_state.budget_total:,}")}
        {metric("Presupuesto Utilizado", f"{st.session_state.budget_used}%")}
        {metric("Tamaño del Equipo", f"{st.session_state.team_size} personas")}
    </div>
    """
    st.markdown(
        card("🎯 Resumen del Proyecto", overview_content), unsafe_allow_html=True
    )

    # Available Pages Card
    pages_content = f"""
    <div style="margin-bottom: 1rem;">
        <div style="margin-bottom: 1rem;">
            <strong>1. {TEXT[lang]['page1_name']}</strong>
            <p style="color: {COLORS['muted']};">{TEXT[lang]['page1_desc']}</p>
        </div>
        <div style="margin-bottom: 1rem;">
            <strong>2. {TEXT[lang]['page2_name']}</strong>
            <p style="color: {COLORS['muted']};">{TEXT[lang]['page2_desc']}</p>
        </div>
        <div style="margin-bottom: 1rem;">
            <strong>3. {TEXT[lang]['page3_name']}</strong>
            <p style="color: {COLORS['muted']};">{TEXT[lang]['page3_desc']}</p>
        </div>
    </div>
    """
    st.markdown(card("📚 Módulos Disponibles", pages_content), unsafe_allow_html=True)

    # Risk Overview Card
    risks_content = "<div style='overflow-x: auto;'><table style='width: 100%;'>"
    risks_content += "<tr><th>Riesgo</th><th>Impacto</th><th>Probabilidad</th><th>Responsable</th></tr>"
    for risk in st.session_state.risks:
        impact_color = COLORS["danger"] if risk["impact"] >= 4 else COLORS["warning"]
        prob_color = (
            COLORS["danger"] if risk["probability"] >= 50 else COLORS["warning"]
        )
        risks_content += f"""
        <tr>
            <td>{risk['name']}</td>
            <td style="color: {impact_color};">{risk['impact']}/5</td>
            <td style="color: {prob_color};">{risk['probability']}%</td>
            <td>{risk['owner']}</td>
        </tr>
        """
    risks_content += "</table></div>"
    st.markdown(card("⚠️ Riesgos Principales", risks_content), unsafe_allow_html=True)

    st.info(TEXT[lang]["select_page_prompt"])

elif st.session_state.selected_page == "page1":
    # Page 1: Interactive Model
    st.title(TEXT[lang]["page1_name"])
    st.markdown("### " + TEXT[lang]["page1_desc"])

    # Placeholder for interactive model content
    st.info(
        "🚧 Modelo Interactivo en desarrollo. Utiliza la navegación lateral para explorar otras secciones."
    )

elif st.session_state.selected_page == "page2":
    # Page 2: Advanced Dashboard with Monte Carlo
    st.title(TEXT[lang]["page2_name"])

    # Calculate current metrics
    delay_migration = max(0, st.session_state.migration_days - 23)
    eficiencia_mig = max(0.5, 1.0 - (delay_migration * 0.05))

    # Simplified quality calculation for display
    valor_original = (
        1.0
        + 0.25
        + 0.40 * eficiencia_mig
        + 0.20
        + 0.15
        + 0.10 * (st.session_state.user_availability / 100)
        + 0.10
    )
    calidad_actual = min(max((valor_original / 2.20) * 100, 0), 100)

    coste_estimado = st.session_state.budget_total * (
        st.session_state.budget_used / 100
    )
    eficiencia_equipo = min(
        100, (st.session_state.team_size * st.session_state.user_availability) / 20
    )

    # Top row with KPI cards
    col1, col2 = st.columns(2)

    with col1:
        # Project Health Card
        health_content = (
            metric("Calidad del Proyecto", f"{calidad_actual:.1f}%")
            + metric("Días Migration", f"{st.session_state.migration_days} días")
            + metric("Eficiencia del Equipo", f"{eficiencia_equipo:.0f}%")
        )
        st.markdown(
            card("🎯 Salud del Proyecto", health_content), unsafe_allow_html=True
        )

    with col2:
        # Financial Metrics Card
        financial_content = (
            metric("Coste Estimado", f"€{coste_estimado:,.0f}")
            + metric("Presupuesto Utilizado", f"{st.session_state.budget_used}%")
            + metric("Tamaño del Equipo", f"{st.session_state.team_size} personas")
        )
        st.markdown(
            card("💰 Métricas Financieras", financial_content), unsafe_allow_html=True
        )

    # Monte Carlo Simulation Card
    st.markdown("### " + TEXT[lang]["montecarlo_header"])

    # Create Monte Carlo card with consistent styling
    monte_carlo_content = f"""
    <div style="margin-bottom: 1.5rem;">
        <div style="margin-bottom: 1rem;">
            <p style="color: {COLORS['muted']}; font-size: 0.9rem;">
                Simulación basada en modelo econométrico con Migration como fase crítica (peso 0.40)
            </p>
        </div>
    </div>
    """

    # Add button and results area
    if st.button("🎲 Ejecutar Simulación (10.000 iteraciones)", type="primary"):
        with st.spinner("Calculando..."):
            # Run Monte Carlo simulation
            results = run_monte_carlo_simulation(iterations=10000, threshold=80)

            # Calculate statistics
            mean_quality = np.mean(results)
            success_prob = (np.sum(np.array(results) >= 80) / len(results)) * 100
            median_quality = np.median(results)
            min_val = np.min(results)
            max_val = np.max(results)

            # Display results with consistent styling
            results_content = metric("Calidad Media", f"{mean_quality:.1f}%") + metric(
                "Probabilidad de Éxito", f"{success_prob:.1f}%"
            )

            # Add summary with muted text styling
            summary_text = f"""
            <div style="color: {COLORS['muted']}; font-size: 0.875rem; margin-top: 1rem;">
                Rango: {min_val:.1f}% - {max_val:.1f}% | Mediana: {median_quality:.1f}%
            </div>
            """

            st.markdown(
                card("📊 Resultados de Simulación", results_content + summary_text),
                unsafe_allow_html=True,
            )

            # Create and display histogram
            st.markdown("### 📊 Distribución de Resultados")

            try:
                fig = px.histogram(
                    results,
                    nbins=50,
                    title="Distribución de Calidad Go-Live (Monte Carlo)",
                    color_discrete_sequence=[COLORS["baseline"]],
                    labels={"value": "Calidad (%)", "count": "Frecuencia"},
                )

                # Apply consistent styling
                fig.update_layout(**PLOT_LAYOUT)
                fig.update_layout(
                    title_font_size=16,
                    title_font_color=COLORS["text"],
                    font_family="system-ui, sans-serif",
                    height=400,  # Ensure adequate height
                )

                # Clean up traces for better appearance
                fig.update_traces(marker_line_width=0, opacity=0.8)

                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error al crear el histograma: {str(e)}")

                # Fallback: Simple bar chart using Streamlit
                st.markdown("**Distribución de Resultados (Fallback):**")

                # Create bins for fallback chart
                bins = np.linspace(min(results), max(results), 20)
                hist, bin_edges = np.histogram(results, bins=bins)

                # Create DataFrame for chart
                chart_data = pd.DataFrame(
                    {
                        "Calidad (%)": [
                            (bin_edges[i] + bin_edges[i + 1]) / 2
                            for i in range(len(hist))
                        ],
                        "Frecuencia": hist,
                    }
                )

                st.bar_chart(chart_data.set_index("Calidad (%)"))

            # Additional statistics
            st.markdown("### 📈 Estadísticas Detalladas")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Media", f"{mean_quality:.1f}%")
            with col2:
                st.metric("Mediana", f"{median_quality:.1f}%")
            with col3:
                st.metric("Mínimo", f"{min_val:.1f}%")
            with col4:
                st.metric("Máximo", f"{max_val:.1f}%")

    # Alerts section
    if delay_migration > 0:
        alert_content = f"""
        <div style="color: {COLORS['danger']}; font-weight: bold; font-size: 0.9rem;">
            🔴 CRÍTICO: Migration con {delay_migration} días de delay
        </div>
        <div style="color: {COLORS['muted']}; font-size: 0.8rem; margin-top: 0.5rem;">
            Impacto estimado: -{(delay_migration * 5):.1f}% en calidad final
        </div>
        """
        st.markdown(card("⚠️ Alertas", alert_content), unsafe_allow_html=True)

elif st.session_state.selected_page == "page3":
    # Page 3: Risk Matrix
    st.title(TEXT[lang]["page3_name"])
    st.markdown("### " + TEXT[lang]["page3_desc"])

    # Placeholder for risk matrix content
    st.info(
        "🚧 Matriz de Riesgo en desarrollo. Utiliza la navegación lateral para explorar otras secciones."
    )

# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: {COLORS['muted']}; font-size: 0.8rem;'>{TEXT[lang]['footer_text']}</div>",
    unsafe_allow_html=True,
)
