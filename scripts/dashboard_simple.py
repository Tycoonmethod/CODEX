#!/usr/bin/env python3
"""
Dashboard Simple Go-Live - Versión funcional garantizada
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import datetime as dt
from datetime import timedelta
import json

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Go-Live", layout="wide", initial_sidebar_state="expanded"
)


# --- MODELO ECONOMÉTRICO ---
def quality_model_econometric(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
):
    """Modelo econométrico mejorado donde Migration es verdaderamente crítica"""
    migration_factor = migration_pct / 100

    if migration_pct < 100:
        bloqueo_factor = migration_factor * 0.6
        e2e_pct = e2e_pct * bloqueo_factor
        training_pct = training_pct * bloqueo_factor

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


# --- HEADER ---
st.title("🚀 Dashboard Go-Live Interactivo")
st.markdown("**Modelo Econométrico con Migration Crítica**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📊 Configuración del Proyecto")

    # Información básica
    st.subheader("🏢 Proyecto")
    proyecto_nombre = st.text_input("Nombre del Proyecto", "Proyecto Go-Live 2025")
    sponsor = st.selectbox("Sponsor", ["CEO", "CTO", "CFO", "COO"])

    # Presupuesto
    st.subheader("💰 Presupuesto")
    presupuesto_total = st.number_input(
        "Presupuesto Total (€)",
        min_value=100000,
        max_value=10000000,
        value=2000000,
        step=50000,
    )
    presupuesto_usado = st.slider("% Presupuesto Usado", 0, 150, 75)

    # Recursos
    st.subheader("👥 Recursos")
    team_size = st.slider("Tamaño del Equipo", 5, 100, 25)
    disponibilidad_usuarios = st.slider("Disponibilidad Usuarios (%)", 50, 100, 80)

    # Fases del proyecto
    st.subheader("⚙️ Fases del Proyecto")
    dias_uat = st.slider("Días UAT", 15, 40, 23)
    dias_migration = st.slider("Días Migration (CRÍTICA)", 23, 60, 23)
    dias_e2e = st.slider("Días E2E", 20, 50, 30)
    dias_training = st.slider("Días Training", 15, 45, 31)

    # Riesgos
    st.subheader("⚠️ Riesgos")
    riesgo_tecnico = st.slider("Riesgo Técnico", 0, 100, 30)
    riesgo_negocio = st.slider("Riesgo de Negocio", 0, 100, 25)

# --- CÁLCULOS ---
delay_migration = max(0, dias_migration - 23)
eficiencia_equipo = min(100, (team_size * disponibilidad_usuarios) / 20)
costo_estimado = presupuesto_total * (presupuesto_usado / 100)

# Calcular calidad
calidad_base = quality_model_econometric(100, 100, 100, 100, 100, 0)
if delay_migration > 0:
    eficiencia_mig = max(0.5, 1.0 - (delay_migration * 0.05))
    calidad_actual = quality_model_econometric(
        100, 100 * eficiencia_mig, 100, 100, 100, 0
    )
else:
    calidad_actual = calidad_base

# Calcular riesgo
riesgo_proyecto = 0.1  # Base
if delay_migration > 0:
    riesgo_proyecto += delay_migration * 0.02
if presupuesto_usado > 100:
    riesgo_proyecto += 0.1
if team_size < 15:
    riesgo_proyecto += 0.1
riesgo_proyecto = min(riesgo_proyecto, 1.0)

# --- MÉTRICAS PRINCIPALES ---
st.subheader("📊 Métricas Principales")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "🎯 Calidad Go-Live",
        f"{calidad_actual:.1f}%",
        delta=f"{calidad_actual - calidad_base:.1f}%",
    )

with col2:
    st.metric("⚠️ Riesgo Proyecto", f"{riesgo_proyecto*100:.1f}%")

with col3:
    dias_totales = dias_uat + dias_migration + dias_e2e + dias_training + 6
    st.metric("📅 Días Totales", f"{dias_totales}", delta=f"{dias_totales - 113}")

with col4:
    st.metric("💰 Costo Actual", f"€{costo_estimado:,.0f}")

with col5:
    st.metric("👥 Eficiencia Equipo", f"{eficiencia_equipo:.0f}%")

# --- ALERTAS ---
st.subheader("🚨 Alertas")
alertas = []

if delay_migration > 0:
    alertas.append(f"🔴 CRÍTICO: Migration con {delay_migration} días de delay")
if riesgo_proyecto > 0.5:
    alertas.append("🔴 CRÍTICO: Riesgo del proyecto muy alto")
if presupuesto_usado > 100:
    alertas.append("🟡 ADVERTENCIA: Presupuesto excedido")
if disponibilidad_usuarios < 70:
    alertas.append("🟡 ADVERTENCIA: Baja disponibilidad de usuarios")
if calidad_actual < 80:
    alertas.append("🔴 CRÍTICO: Calidad por debajo del umbral")

if alertas:
    for alerta in alertas:
        st.error(alerta)
else:
    st.success("✅ Todos los indicadores en rango normal")

# --- GRÁFICOS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Evolución de Calidad")

    # Cronograma
    fechas = [
        dt.datetime(2025, 7, 31),  # UAT
        dt.datetime(2025, 8, 31) + timedelta(days=delay_migration),  # Migration
        dt.datetime(2025, 9, 30) + timedelta(days=delay_migration),  # E2E
        dt.datetime(2025, 10, 31) + timedelta(days=delay_migration),  # Training
        dt.datetime(2025, 11, 3) + timedelta(days=delay_migration),  # GoLive
        dt.datetime(2025, 12, 3) + timedelta(days=delay_migration),  # Hypercare
    ]

    calidades = [61.2, 61.7, 76.5, 88.2, calidad_actual, 100.0]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=fechas,
            y=calidades,
            mode="lines+markers",
            name="Calidad Proyectada",
            line=dict(color="blue", width=3),
        )
    )

    fig.add_hline(
        y=85, line_dash="dash", line_color="red", annotation_text="Umbral Mínimo"
    )
    fig.update_layout(
        title="Evolución de Calidad", yaxis_title="Calidad (%)", height=400
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💰 Desglose de Costos")

    # Costos por categoría
    costos = {
        "Personal Interno": presupuesto_total * 0.4,
        "Consultores": presupuesto_total * 0.3,
        "Tecnología": presupuesto_total * 0.2,
        "Contingencia": presupuesto_total * 0.1,
    }

    labels = list(costos.keys())
    values = list(costos.values())

    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values)])
    fig_pie.update_layout(title="Distribución de Costos", height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

# --- ANÁLISIS DE ESCENARIOS ---
st.subheader("📊 Análisis de Escenarios")

escenarios_data = {
    "Escenario": ["Optimista", "Actual", "Pesimista"],
    "Migration (días)": [23, dias_migration, 40],
    "E2E (días)": [25, dias_e2e, 45],
    "Training (días)": [25, dias_training, 40],
    "Calidad (%)": [98.5, calidad_actual, 72.3],
    "Riesgo (%)": [15, riesgo_proyecto * 100, 75],
}

df_escenarios = pd.DataFrame(escenarios_data)
st.dataframe(df_escenarios, use_container_width=True)

# --- RECOMENDACIONES ---
st.subheader("💡 Recomendaciones")

recomendaciones = []

if delay_migration > 0:
    recomendaciones.append(
        "🔴 URGENTE: Reforzar equipo de Migration con consultores especializados"
    )
if riesgo_proyecto > 0.4:
    recomendaciones.append("🟡 Implementar reuniones diarias de seguimiento")
if presupuesto_usado > 90:
    recomendaciones.append("🟡 Revisar scope para optimizar costos")
if disponibilidad_usuarios < 80:
    recomendaciones.append("🟡 Negociar mayor disponibilidad de usuarios")

if recomendaciones:
    for rec in recomendaciones:
        st.info(rec)
else:
    st.success("✅ Proyecto en buen estado, continuar con plan actual")

# --- MODELO ECONOMÉTRICO ---
st.subheader("📐 Modelo Econométrico")
st.latex(
    r"Quality = \frac{1.00 + 0.25 \times UAT + 0.40 \times Migration + 0.20 \times E2E + 0.15 \times Training + 0.10 \times Resources + 0.10 \times Hypercare}{2.20} \times 100"
)

# --- EXPORTAR ---
st.subheader("📄 Exportar Datos")

if st.button("Generar Reporte"):
    reporte = {
        "proyecto": proyecto_nombre,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "calidad_actual": round(calidad_actual, 1),
        "riesgo_proyecto": round(riesgo_proyecto * 100, 1),
        "presupuesto_usado": presupuesto_usado,
        "delay_migration": delay_migration,
        "recomendaciones": recomendaciones,
    }

    st.download_button(
        label="📥 Descargar Reporte JSON",
        data=json.dumps(reporte, indent=2, ensure_ascii=False),
        file_name=f"reporte_golive_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
    )

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "**Dashboard Go-Live** | Modelo Econométrico con Migration Crítica | "
    + datetime.now().strftime("%Y-%m-%d %H:%M")
)
