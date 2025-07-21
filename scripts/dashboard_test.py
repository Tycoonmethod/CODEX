import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import numpy as np

# Configuración
st.set_page_config(page_title="Dashboard Go-Live Avanzado", layout="wide")

# Título
st.title("🚀 Dashboard Go-Live Avanzado")
st.markdown("**Análisis integral con inputs de negocio y simulaciones**")

# Sidebar con inputs
with st.sidebar:
    st.header("📊 Inputs de Negocio")

    # Proyecto
    st.subheader("🏢 Proyecto")
    proyecto = st.text_input("Nombre", "Proyecto Go-Live 2025")
    sponsor = st.selectbox("Sponsor", ["CEO", "CTO", "CFO", "COO"])
    criticidad = st.selectbox("Criticidad", ["Baja", "Media", "Alta", "Crítica"])

    # Presupuesto
    st.subheader("💰 Presupuesto")
    presupuesto = st.number_input("Total (€)", value=2000000, step=50000)
    pct_usado = st.slider("% Usado", 0, 150, 75)

    # Recursos
    st.subheader("👥 Recursos")
    team_size = st.slider("Tamaño Equipo", 5, 100, 25)
    consultores = st.slider("Consultores", 0, 20, 5)
    disponibilidad = st.slider("Disponibilidad (%)", 50, 100, 80)

    # Fases
    st.subheader("⚙️ Fases")
    uat_dias = st.slider("UAT (días)", 15, 40, 23)
    mig_dias = st.slider("Migration (días)", 23, 60, 23)
    e2e_dias = st.slider("E2E (días)", 20, 50, 30)
    train_dias = st.slider("Training (días)", 15, 45, 31)

    # Riesgos
    st.subheader("⚠️ Riesgos")
    riesgo_tec = st.slider("Técnico", 0, 100, 30)
    riesgo_neg = st.slider("Negocio", 0, 100, 25)
    cambios = st.slider("Cambios Scope (%)", 0, 50, 10)

# Cálculos
delay = max(0, mig_dias - 23)
costo = presupuesto * (pct_usado / 100)
riesgo_total = (riesgo_tec + riesgo_neg + cambios + (delay * 5)) / 4
calidad = max(50, 95 - (delay * 2) - (riesgo_total * 0.3))

# Métricas principales
st.subheader("📊 Métricas Principales")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("🎯 Calidad Go-Live", f"{calidad:.1f}%")
with col2:
    st.metric("⚠️ Riesgo Total", f"{riesgo_total:.1f}%")
with col3:
    st.metric("📅 Delay Migration", f"{delay} días")
with col4:
    st.metric("💰 Costo Actual", f"€{costo:,.0f}")
with col5:
    st.metric("👥 Eficiencia", f"{min(100, team_size * 2):.0f}%")

# Alertas
st.subheader("🚨 Alertas Automáticas")
if delay > 0:
    st.error(f"🔴 CRÍTICO: Migration con {delay} días de delay")
if riesgo_total > 50:
    st.error("🔴 CRÍTICO: Riesgo muy alto")
if pct_usado > 100:
    st.warning("🟡 ADVERTENCIA: Presupuesto excedido")
if calidad < 80:
    st.error("🔴 CRÍTICO: Calidad baja")
if delay == 0 and riesgo_total < 40 and pct_usado < 100:
    st.success("✅ Todos los indicadores normales")

# Gráficos
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Evolución de Calidad")
    fechas = ["Jul-31", "Aug-31", "Sep-30", "Oct-31", "Nov-03", "Dec-03"]
    valores = [61.2, 61.7, 76.5, 88.2, calidad, min(100, calidad + 10)]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=fechas, y=valores, mode="lines+markers"))
    fig1.add_hline(y=85, line_dash="dash", line_color="red")
    fig1.update_layout(title="Proyección de Calidad", height=300)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🎲 Análisis de Riesgo")
    categorias = ["Técnico", "Negocio", "Presupuesto", "Recursos", "Tiempo"]
    valores_riesgo = [
        riesgo_tec,
        riesgo_neg,
        max(0, pct_usado - 100),
        100 - disponibilidad,
        delay * 5,
    ]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatterpolar(r=valores_riesgo, theta=categorias, fill="toself"))
    fig2.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=300)
    st.plotly_chart(fig2, use_container_width=True)

# Simulación Monte Carlo
st.subheader("🎯 Simulación Monte Carlo")
if st.button("Ejecutar Simulación"):
    # Generar datos simulados
    np.random.seed(42)
    resultados = np.random.normal(calidad, 10, 1000)
    resultados = np.clip(resultados, 0, 100)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Media", f"{np.mean(resultados):.1f}%")
    with col2:
        st.metric("Desv. Std", f"{np.std(resultados):.1f}%")
    with col3:
        st.metric("Prob. Éxito", f"{(resultados >= 85).mean()*100:.1f}%")

    # Histograma
    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(x=resultados, nbinsx=30))
    fig3.add_vline(x=85, line_dash="dash", line_color="red")
    fig3.update_layout(title="Distribución de Resultados", height=300)
    st.plotly_chart(fig3, use_container_width=True)

# Análisis financiero
st.subheader("💰 Análisis Financiero")
col1, col2 = st.columns(2)

with col1:
    # Costos
    costos = {
        "Personal": presupuesto * 0.4,
        "Consultores": presupuesto * 0.3,
        "Tecnología": presupuesto * 0.2,
        "Otros": presupuesto * 0.1,
    }

    fig4 = go.Figure()
    fig4.add_trace(go.Pie(labels=list(costos.keys()), values=list(costos.values())))
    fig4.update_layout(title="Distribución de Costos", height=300)
    st.plotly_chart(fig4, use_container_width=True)

with col2:
    # ROI
    beneficio = st.number_input("Beneficio Anual (€)", value=5000000)
    roi = ((beneficio - presupuesto) / presupuesto) * 100
    payback = (presupuesto / beneficio) * 12

    st.metric("ROI Año 1", f"{roi:.1f}%")
    st.metric("Payback", f"{payback:.1f} meses")

# Escenarios
st.subheader("📊 Comparación de Escenarios")
escenarios = pd.DataFrame(
    {
        "Escenario": ["Optimista", "Actual", "Pesimista"],
        "Migration": [23, mig_dias, 40],
        "Calidad": [98.5, calidad, 70.0],
        "Riesgo": [15, riesgo_total, 75],
    }
)
st.dataframe(escenarios, use_container_width=True)

# Recomendaciones
st.subheader("💡 Recomendaciones Automáticas")
if delay > 0:
    st.info("🔴 URGENTE: Reforzar equipo Migration")
if riesgo_total > 40:
    st.info("🟡 Implementar seguimiento diario")
if pct_usado > 90:
    st.info("🟡 Revisar scope del proyecto")

# Exportar
st.subheader("📄 Exportar Reporte")
if st.button("Generar Reporte"):
    reporte = {
        "proyecto": proyecto,
        "calidad": calidad,
        "riesgo": riesgo_total,
        "delay": delay,
        "costo": costo,
    }
    st.download_button("Descargar", str(reporte), "reporte.json")

st.markdown("---")
st.markdown(
    "**Dashboard Go-Live Avanzado** | Modelo Econométrico | "
    + datetime.now().strftime("%Y-%m-%d %H:%M")
)
