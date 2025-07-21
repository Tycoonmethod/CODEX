#!/usr/bin/env python3
"""
Dashboard Avanzado e Interactivo para Go-Live
Incluye inputs de negocio relevantes y análisis avanzados
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import calendar
from scipy import stats
import json

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Go-Live Avanzado",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- MODELO ECONOMÉTRICO CON MIGRATION CRÍTICA ---
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


# --- FUNCIÓN DE CÁLCULO DE RIESGO ---
def calcular_riesgo_proyecto(
    migration_days, e2e_days, training_days, team_size, budget_pct
):
    """Calcula el riesgo general del proyecto basado en múltiples factores"""
    riesgo_base = 0.1  # 10% de riesgo base

    # Riesgo por delays
    if migration_days > 23:
        riesgo_base += (migration_days - 23) * 0.02
    if e2e_days > 30:
        riesgo_base += (e2e_days - 30) * 0.01
    if training_days > 31:
        riesgo_base += (training_days - 31) * 0.01

    # Riesgo por tamaño del equipo
    if team_size < 10:
        riesgo_base += 0.15  # Equipo pequeño
    elif team_size > 50:
        riesgo_base += 0.10  # Equipo muy grande

    # Riesgo por presupuesto
    if budget_pct < 80:
        riesgo_base += 0.20  # Presupuesto insuficiente
    elif budget_pct > 120:
        riesgo_base += 0.05  # Sobrepresupuesto

    return min(riesgo_base, 1.0)


# --- SIMULACIÓN MONTE CARLO ---
def simulacion_monte_carlo(scenarios, n_simulations=1000):
    """Ejecuta simulación Monte Carlo para análisis de riesgo"""
    resultados = []

    for _ in range(n_simulations):
        # Variabilidad aleatoria en días (+/- 20%)
        uat_var = np.random.normal(1.0, 0.1)
        migration_var = np.random.normal(1.0, 0.15)  # Mayor variabilidad para Migration
        e2e_var = np.random.normal(1.0, 0.1)
        training_var = np.random.normal(1.0, 0.1)

        # Aplicar variabilidad
        uat_sim = max(scenarios["UAT"] * uat_var, 15)
        migration_sim = max(scenarios["Migration"] * migration_var, 23)
        e2e_sim = max(scenarios["E2E"] * e2e_var, 20)
        training_sim = max(scenarios["Training"] * training_var, 15)

        # Calcular calidad con variabilidad
        calidad = quality_model_econometric(100, 100, 100, 100, 100, 0)

        # Aplicar penalizaciones por delays
        if migration_sim > 23:
            delay_migration = migration_sim - 23
            eficiencia = max(0.5, 1.0 - (delay_migration * 0.05))
            calidad = quality_model_econometric(100, 100 * eficiencia, 100, 100, 100, 0)

        resultados.append(
            {
                "calidad": calidad,
                "migration_days": migration_sim,
                "total_days": uat_sim + migration_sim + e2e_sim + training_sim,
            }
        )

    return pd.DataFrame(resultados)


# --- HEADER DEL DASHBOARD ---
st.title("🚀 Dashboard Go-Live Avanzado")
st.markdown("**Análisis integral con inputs de negocio y simulaciones avanzadas**")

# --- SIDEBAR CON INPUTS DE NEGOCIO ---
with st.sidebar:
    st.header("📊 Inputs de Negocio")

    # Información del proyecto
    st.subheader("🏢 Información del Proyecto")
    proyecto_nombre = st.text_input("Nombre del Proyecto", "Proyecto Go-Live 2025")
    sponsor = st.selectbox("Sponsor Ejecutivo", ["CEO", "CTO", "CFO", "COO"])
    criticidad = st.selectbox(
        "Criticidad del Proyecto", ["Baja", "Media", "Alta", "Crítica"]
    )

    # Recursos y presupuesto
    st.subheader("💰 Recursos y Presupuesto")
    presupuesto_total = st.number_input(
        "Presupuesto Total (€)",
        min_value=100000,
        max_value=10000000,
        value=2000000,
        step=50000,
    )
    presupuesto_usado = st.slider("% Presupuesto Usado", 0, 150, 75)
    team_size = st.slider("Tamaño del Equipo", 5, 100, 25)
    consultores_externos = st.slider("Consultores Externos", 0, 20, 5)

    # Configuración de fases
    st.subheader("⚙️ Configuración de Fases")
    dias_uat = st.slider("Días UAT", 15, 40, 23)
    dias_migration = st.slider("Días Migration (CRÍTICA)", 23, 60, 23)
    dias_e2e = st.slider("Días E2E", 20, 50, 30)
    dias_training = st.slider("Días Training", 15, 45, 31)

    # Factores de riesgo
    st.subheader("⚠️ Factores de Riesgo")
    riesgo_tecnico = st.slider("Riesgo Técnico", 0, 100, 30)
    riesgo_negocio = st.slider("Riesgo de Negocio", 0, 100, 25)
    cambios_scope = st.slider("Cambios en Scope (%)", 0, 50, 10)
    disponibilidad_usuarios = st.slider("Disponibilidad Usuarios (%)", 50, 100, 80)

# --- CÁLCULOS PRINCIPALES ---
dias_config = {
    "UAT": dias_uat,
    "Migration": dias_migration,
    "E2E": dias_e2e,
    "Training": dias_training,
    "GoLive": 6,
}

# Calcular métricas
delay_migration = max(0, dias_migration - 23)
riesgo_proyecto = calcular_riesgo_proyecto(
    dias_migration, dias_e2e, dias_training, team_size, presupuesto_usado
)
calidad_actual = quality_model_econometric(100, 100, 100, 100, 100, 0)

# Aplicar penalizaciones
if delay_migration > 0:
    eficiencia_mig = max(0.5, 1.0 - (delay_migration * 0.05))
    calidad_actual = quality_model_econometric(
        100, 100 * eficiencia_mig, 100, 100, 100, 0
    )

# --- MÉTRICAS PRINCIPALES ---
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    color_calidad = (
        "normal"
        if calidad_actual >= 90
        else "inverse" if calidad_actual >= 80 else "off"
    )
    st.metric(
        "🎯 Calidad Go-Live",
        f"{calidad_actual:.1f}%",
        delta=f"{calidad_actual - 95.5:.1f}%",
    )

with col2:
    color_riesgo = (
        "off"
        if riesgo_proyecto >= 0.5
        else "inverse" if riesgo_proyecto >= 0.3 else "normal"
    )
    st.metric("⚠️ Riesgo Proyecto", f"{riesgo_proyecto*100:.1f}%")

with col3:
    dias_totales = sum(dias_config.values())
    st.metric("📅 Días Totales", f"{dias_totales}", delta=f"{dias_totales - 113}")

with col4:
    costo_estimado = presupuesto_total * (presupuesto_usado / 100)
    st.metric("💰 Costo Actual", f"€{costo_estimado:,.0f}")

with col5:
    eficiencia_equipo = min(100, (team_size * disponibilidad_usuarios) / 20)
    st.metric("👥 Eficiencia Equipo", f"{eficiencia_equipo:.0f}%")

# --- ALERTAS AUTOMÁTICAS ---
st.subheader("🚨 Alertas Automáticas")

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

# --- GRÁFICOS PRINCIPALES ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Evolución de Calidad")

    # Crear cronograma
    fechas = [
        datetime(2025, 7, 31),  # UAT
        datetime(2025, 8, 31) + timedelta(days=delay_migration),  # Migration
        datetime(2025, 9, 30) + timedelta(days=delay_migration),  # E2E
        datetime(2025, 10, 31) + timedelta(days=delay_migration),  # Training
        datetime(2025, 11, 3) + timedelta(days=delay_migration),  # GoLive
        datetime(2025, 12, 3) + timedelta(days=delay_migration),  # Hypercare
    ]

    calidades = [61.2, 61.7, 76.5, 88.2, calidad_actual, 100.0]

    fig_evolucion = go.Figure()
    fig_evolucion.add_trace(
        go.Scatter(
            x=fechas,
            y=calidades,
            mode="lines+markers",
            name="Calidad Proyectada",
            line=dict(color="blue", width=3),
        )
    )

    fig_evolucion.add_hline(
        y=85, line_dash="dash", line_color="red", annotation_text="Umbral Mínimo"
    )
    fig_evolucion.update_layout(
        title="Evolución de Calidad del Proyecto", yaxis_title="Calidad (%)"
    )
    st.plotly_chart(fig_evolucion, use_container_width=True)

with col2:
    st.subheader("🎲 Análisis de Riesgo")

    # Gráfico de riesgo por categoría
    categorias_riesgo = ["Técnico", "Negocio", "Presupuesto", "Recursos", "Tiempo"]
    valores_riesgo = [
        riesgo_tecnico,
        riesgo_negocio,
        presupuesto_usado - 100 if presupuesto_usado > 100 else 0,
        100 - eficiencia_equipo,
        delay_migration * 5,
    ]

    fig_riesgo = go.Figure(
        data=go.Scatterpolar(
            r=valores_riesgo,
            theta=categorias_riesgo,
            fill="toself",
            name="Riesgo Actual",
        )
    )
    fig_riesgo.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Análisis de Riesgo por Categoría",
    )
    st.plotly_chart(fig_riesgo, use_container_width=True)

# --- SIMULACIÓN MONTE CARLO ---
st.subheader("🎯 Simulación Monte Carlo")

if st.button("Ejecutar Simulación (1000 iteraciones)"):
    with st.spinner("Ejecutando simulación..."):
        resultados_mc = simulacion_monte_carlo(dias_config)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Calidad Media", f"{resultados_mc['calidad'].mean():.1f}%")
        st.metric("Desviación Estándar", f"{resultados_mc['calidad'].std():.1f}%")

    with col2:
        percentil_10 = resultados_mc["calidad"].quantile(0.1)
        percentil_90 = resultados_mc["calidad"].quantile(0.9)
        st.metric("Percentil 10%", f"{percentil_10:.1f}%")
        st.metric("Percentil 90%", f"{percentil_90:.1f}%")

    with col3:
        prob_exito = (resultados_mc["calidad"] >= 85).mean() * 100
        st.metric("Probabilidad Éxito", f"{prob_exito:.1f}%")

    # Histograma de resultados
    fig_hist = px.histogram(
        resultados_mc,
        x="calidad",
        nbins=50,
        title="Distribución de Calidad (Monte Carlo)",
    )
    fig_hist.add_vline(
        x=85, line_dash="dash", line_color="red", annotation_text="Umbral"
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# --- ANÁLISIS FINANCIERO ---
st.subheader("💰 Análisis Financiero")

col1, col2 = st.columns(2)

with col1:
    # Desglose de costos
    costos = {
        "Personal Interno": presupuesto_total * 0.4,
        "Consultores": presupuesto_total * 0.3,
        "Tecnología": presupuesto_total * 0.2,
        "Contingencia": presupuesto_total * 0.1,
    }

    fig_costos = px.pie(
        values=list(costos.values()),
        names=list(costos.keys()),
        title="Desglose de Costos",
    )
    st.plotly_chart(fig_costos, use_container_width=True)

with col2:
    # ROI proyectado
    beneficio_anual = st.number_input(
        "Beneficio Anual Esperado (€)",
        min_value=100000,
        max_value=50000000,
        value=5000000,
    )

    roi_1_year = ((beneficio_anual - presupuesto_total) / presupuesto_total) * 100
    payback_months = (presupuesto_total / beneficio_anual) * 12

    st.metric("ROI Año 1", f"{roi_1_year:.1f}%")
    st.metric("Payback (meses)", f"{payback_months:.1f}")

# --- COMPARACIÓN DE ESCENARIOS ---
st.subheader("📊 Comparación de Escenarios")

escenarios = {
    "Optimista": {"Migration": 23, "E2E": 25, "Training": 25, "Calidad": 98.5},
    "Realista": {
        "Migration": dias_migration,
        "E2E": dias_e2e,
        "Training": dias_training,
        "Calidad": calidad_actual,
    },
    "Pesimista": {"Migration": 40, "E2E": 45, "Training": 40, "Calidad": 72.3},
}

df_escenarios = pd.DataFrame(escenarios).T
st.dataframe(df_escenarios, use_container_width=True)

# --- RECOMENDACIONES AUTOMÁTICAS ---
st.subheader("💡 Recomendaciones Automáticas")

recomendaciones = []

if delay_migration > 0:
    recomendaciones.append(
        "🔴 URGENTE: Reforzar equipo de Migration con consultores especializados"
    )
if riesgo_proyecto > 0.4:
    recomendaciones.append("🟡 Implementar reuniones diarias de seguimiento de riesgos")
if presupuesto_usado > 90:
    recomendaciones.append("🟡 Revisar scope del proyecto para optimizar costos")
if disponibilidad_usuarios < 80:
    recomendaciones.append("🟡 Negociar mayor disponibilidad de usuarios clave")
if calidad_actual < 90:
    recomendaciones.append("🔴 Considerar retrasar Go-Live para mejorar calidad")

if recomendaciones:
    for rec in recomendaciones:
        st.info(rec)
else:
    st.success("✅ Proyecto en buen estado, continuar con plan actual")

# --- EXPORTAR REPORTE ---
st.subheader("📄 Exportar Reporte")

if st.button("Generar Reporte Ejecutivo"):
    reporte = {
        "proyecto": proyecto_nombre,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "calidad_actual": calidad_actual,
        "riesgo_proyecto": riesgo_proyecto,
        "presupuesto_usado": presupuesto_usado,
        "dias_delay": delay_migration,
        "recomendaciones": recomendaciones,
    }

    st.download_button(
        label="Descargar Reporte JSON",
        data=json.dumps(reporte, indent=2),
        file_name=f"reporte_golive_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
    )

    st.success("Reporte generado exitosamente!")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "**Dashboard Go-Live Avanzado** | Modelo Econométrico con Migration Crítica | Actualizado en tiempo real"
)
