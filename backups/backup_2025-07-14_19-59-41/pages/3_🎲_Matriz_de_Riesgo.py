import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from translations import TEXT, LANGUAGES
from styles import COLORS, inject_custom_css, card, metric, PLOT_LAYOUT

# Inject custom CSS
inject_custom_css()


# --- State Initialization (Robust, In-Page) ---
def initialize_state():
    defaults = {
        "lang": "es",
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()
lang = st.session_state.lang

# --- Page Config ---
st.set_page_config(page_title=TEXT[lang]["page3_name"], layout="wide")

# Create a container for the main content
main_container = st.container()

# Sidebar with collapsible configuration
with st.sidebar:
    st.markdown("### ⚙️ Gestión de Riesgos")

    # Risk form in an expander
    with st.expander("➕ Añadir Nuevo Riesgo", expanded=True):
        with st.form("risk_form"):
            risk_name = st.text_input(TEXT[lang]["risk_name"])
            risk_impact = st.slider(TEXT[lang]["risk_impact"], 1, 5, 3)
            risk_probability = st.slider(TEXT[lang]["risk_probability"], 0, 100, 50)
            submitted = st.form_submit_button(TEXT[lang]["add_risk"])
            if submitted and risk_name:
                st.session_state.risks.append(
                    {
                        "name": risk_name,
                        "impact": risk_impact,
                        "probability": risk_probability,
                        "owner": "No asignado",
                    }
                )
                st.rerun()

# --- Risk Data Initialization ---
if "risks" not in st.session_state:
    st.session_state.risks = [
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
        {
            "name": "Baja disponibilidad de usuarios para UAT",
            "impact": 3,
            "probability": 50,
            "owner": "Líder de Negocio",
        },
        {
            "name": "Fallos técnicos en entorno de producción",
            "impact": 5,
            "probability": 20,
            "owner": "Equipo de IT",
        },
    ]

# Main content area with cards
with main_container:
    st.title(TEXT[lang]["page3_name"])

    # Risk Summary Card
    df_risks = pd.DataFrame(st.session_state.risks)
    risk_summary = f"""
    <div style='margin-bottom: 1rem;'>
        {metric("Total de Riesgos", str(len(df_risks)))}
        {metric("Riesgos Críticos", str(len(df_risks[df_risks['impact'] >= 4])))}
        {metric("Probabilidad Media", f"{df_risks['probability'].mean():.1f}%")}
    </div>
    """
    st.markdown(card("📊 Resumen de Riesgos", risk_summary), unsafe_allow_html=True)

    # Risk Matrix Card
    st.markdown(card("🎯 Matriz de Riesgo", ""), unsafe_allow_html=True)

    # Define colors for quadrants using our color palette
    colors = {
        "Low": "rgba(40, 167, 69, 0.6)",  # Success green
        "Medium": "rgba(255, 193, 7, 0.6)",  # Warning yellow
        "High": "rgba(255, 165, 0, 0.6)",  # Orange
        "Critical": "rgba(220, 53, 69, 0.6)",  # Danger red
    }

    def get_color(impact, probability):
        if impact <= 2 and probability <= 50:
            return colors["Low"]
        if impact <= 3 and probability <= 70:
            return colors["Medium"]
        if impact <= 4 and probability <= 85:
            return colors["High"]
        return colors["Critical"]

    df_risks["color"] = df_risks.apply(
        lambda row: get_color(row["impact"], row["probability"]), axis=1
    )

    fig = go.Figure()

    # Add scatter plot for risks
    fig.add_trace(
        go.Scatter(
            x=df_risks["probability"],
            y=df_risks["impact"],
            mode="markers+text",
            text=df_risks["name"],
            textposition="top center",
            marker=dict(
                size=[
                    (p / 10 + i * 5)
                    for p, i in zip(df_risks["probability"], df_risks["impact"])
                ],
                color=df_risks["color"],
                sizemode="diameter",
                showscale=False,
            ),
        )
    )

    # Add quadrant lines and annotations
    fig.add_shape(
        type="line",
        x0=50,
        y0=0,
        x1=50,
        y1=5.5,
        line=dict(color="rgba(255,255,255,0.2)", width=2, dash="dot"),
    )
    fig.add_shape(
        type="line",
        x0=0,
        y0=2.5,
        x1=100,
        y1=2.5,
        line=dict(color="rgba(255,255,255,0.2)", width=2, dash="dot"),
    )

    # Add quadrant labels
    fig.add_annotation(
        x=25, y=5, text="Bajo/Medio", showarrow=False, font=dict(color=COLORS["text"])
    )
    fig.add_annotation(
        x=75, y=5, text="Alto/Crítico", showarrow=False, font=dict(color=COLORS["text"])
    )

    # Update layout with our custom style
    layout_config = PLOT_LAYOUT.copy()
    layout_config.update(
        {
            "height": 600,
            "showlegend": False,
            "title": {
                "text": "Matriz de Riesgo del Proyecto",
                "font": {"size": 20, "color": COLORS["text"]},
            },
            "xaxis": {
                **layout_config.get("xaxis", {}),
                "title": "Probabilidad (%)",
                "range": [0, 105],
            },
            "yaxis": {
                **layout_config.get("yaxis", {}),
                "title": "Impacto (1-5)",
                "range": [0.5, 5.5],
            },
        }
    )
    fig.update_layout(**layout_config)

    st.plotly_chart(fig, use_container_width=True)

    # Risk Table Card
    table_content = "<div style='overflow-x: auto;'><table style='width: 100%;'>"
    table_content += "<tr><th>Riesgo</th><th>Impacto</th><th>Probabilidad</th><th>Responsable</th><th>Nivel</th></tr>"

    for _, risk in df_risks.iterrows():
        risk_level = (
            "Crítico 🔴"
            if risk["impact"] >= 4 and risk["probability"] > 50
            else (
                "Alto 🟠"
                if risk["impact"] >= 3 and risk["probability"] > 30
                else "Medio 🟡" if risk["impact"] >= 2 else "Bajo 🟢"
            )
        )

        table_content += f"""
        <tr>
            <td>{risk['name']}</td>
            <td>{risk['impact']}/5</td>
            <td>{risk['probability']}%</td>
            <td>{risk['owner']}</td>
            <td>{risk_level}</td>
        </tr>
        """

    table_content += "</table></div>"
    st.markdown(card("📋 Detalle de Riesgos", table_content), unsafe_allow_html=True)
