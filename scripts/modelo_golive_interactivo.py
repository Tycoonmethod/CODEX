import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import datetime as dt
from datetime import timedelta
import calendar

# --- Benchmarks con períodos reales ---
benchmarks = {
    "UAT": {
        "min": 15,
        "max": 30,
        "period": ("2025-07-08", "2025-07-31"),
        "available_days": 23,
    },
    "Migration": {
        "min": 28,
        "max": 40,
        "period": ("2025-08-01", "2025-08-31"),
        "available_days": 23,
    },
    "E2E": {
        "min": 20,
        "max": 40,
        "period": ("2025-09-01", "2025-09-30"),
        "available_days": 30,
    },
    "Training": {
        "min": 15,
        "max": 35,
        "period": ("2025-10-01", "2025-10-31"),
        "available_days": 31,
    },
    "GoLive": {
        "min": 6,
        "max": 6,
        "period": ("2025-11-03", "2025-11-08"),
        "available_days": 6,
    },
}

# --- Valores baseline usando Available Days reales ---
baseline_days = {
    "UAT": 23,
    "Migration": 23,  # Fecha límite: 31 de julio (23 días desde 1 agosto)
    "E2E": 30,
    "Training": 31,
    "GoLive": 6,
}

# --- Fechas baseline críticas ---
baseline_fechas = {
    "UAT": dt.datetime(2025, 7, 31),  # Completa el 31 de julio
    "Migration": dt.datetime(2025, 8, 31),  # Fecha límite crítica: 31 de agosto
    "E2E": dt.datetime(2025, 9, 30),  # Habilitada después de Migration
    "Training": dt.datetime(2025, 10, 31),  # Habilitada después de Migration
    "GoLive": dt.datetime(2025, 11, 3),  # Fecha fija del Go-Live
}

# --- Fechas clave para la tabla temporal ---
fechas_clave = [
    dt.datetime(2025, 8, 1),
    dt.datetime(2025, 9, 1),
    dt.datetime(2025, 10, 1),
    dt.datetime(2025, 11, 3),  # Go-Live
    dt.datetime(2025, 12, 3),
]


# --- MODELO ECONOMÉTRICO CON MIGRATION CRÍTICA ---
def quality_model_econometric(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
):
    """
    Modelo econométrico mejorado donde Migration es verdaderamente crítica:
    - Migration bloquea E2E y Training si no está completa
    - Mayor peso para Migration (0.40 vs 0.20 original)
    - Penalización severa por delays en Migration

    Variables van de 0 a 100 (% de completitud)
    """
    # Migration como multiplicador crítico
    migration_factor = migration_pct / 100

    # Si Migration no está completa, E2E y Training se ven severamente afectados
    if migration_pct < 100:
        # Factor de bloqueo: E2E y Training dependen críticamante de Migration
        bloqueo_factor = migration_factor * 0.6  # Reducción severa
        e2e_pct = e2e_pct * bloqueo_factor
        training_pct = training_pct * bloqueo_factor

    # Modelo con Migration como fase crítica
    valor_original = (
        1.00  # Intercepto reducido
        + 0.25 * (uat_pct / 100)  # UAT: peso reducido
        + 0.40 * (migration_pct / 100)  # Migration: peso DUPLICADO (crítica)
        + 0.20 * (e2e_pct / 100)  # E2E: peso aumentado
        + 0.15 * (training_pct / 100)  # Training: peso aumentado
        + 0.10 * (resources_pct / 100)  # Resources: igual
        + 0.10 * (hypercare_pct / 100)  # Hypercare: peso reducido
    )

    # Factor de normalización: 1.00 + 0.25 + 0.40 + 0.20 + 0.15 + 0.10 + 0.10 = 2.20
    factor_normalizacion = 2.20

    # Calidad normalizada entre 0% y 100%
    calidad_normalizada = (valor_original / factor_normalizacion) * 100

    return min(max(calidad_normalizada, 0), 100)  # Asegurar rango 0-100%


def business_days(start, end):
    if start > end:
        return 0
    days = np.busday_count(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    return int(days)


# --- Streamlit UI ---
st.set_page_config(page_title="Modelo Econométrico Go-Live", layout="wide")
st.title("Modelo Econométrico Go-Live - Análisis de Calidad Temporal")
st.markdown(
    "**Migration es la fase crítica** que habilita E2E y Training. Fecha límite Migration: 31 de agosto."
)

# --- Sliders para días por fase (Escenario) ---
st.sidebar.header("Ajuste de días por fase - Escenario")
dias_esc = {}
for fase in ["UAT", "Migration", "E2E", "Training", "GoLive"]:
    minv = benchmarks[fase]["min"]
    maxv = benchmarks[fase]["max"]
    val = baseline_days[fase]

    if minv == maxv:
        dias_esc[fase] = st.sidebar.number_input(
            f"{fase} (Baseline: {val} días)",
            min_value=minv,
            max_value=maxv,
            value=val,
            key=f"esc_{fase}",
        )
    else:
        dias_esc[fase] = st.sidebar.slider(
            f"{fase} (Baseline: {val} días, Rango: {minv}-{maxv})",
            min_value=minv,
            max_value=maxv,
            value=val,
            key=f"esc_{fase}",
        )

# --- Análisis de delay crítico en Migration ---
st.sidebar.header("Estado Migration (Fase Crítica)")
migration_limit_date = dt.datetime(2025, 8, 31)
migration_actual_end = dt.datetime(2025, 8, 1) + timedelta(days=dias_esc["Migration"])
delay_migration = max(0, (migration_actual_end - migration_limit_date).days)

if delay_migration > 0:
    st.sidebar.error(f"🚨 DELAY CRÍTICO: {delay_migration} días")
    st.sidebar.error(f"📅 Fin Migration: {migration_actual_end.strftime('%Y-%m-%d')}")
    st.sidebar.warning("⚠️ E2E y Training se desplazan hacia la derecha")
else:
    st.sidebar.success(f"✅ Migration en plazo")
    st.sidebar.success(f"📅 Fin Migration: {migration_actual_end.strftime('%Y-%m-%d')}")


# --- Función para calcular % de completitud de fase ---
def calcular_completitud_fase(dias_usados, dias_optimos, eficiencia_temporal=1.0):
    """
    Calcula el % de completitud de una fase basado en:
    - Eficiencia de días: días usados vs días óptimos
    - Eficiencia temporal: penalización por delays
    """
    eficiencia_dias = min(dias_usados / dias_optimos, 1.0) * 100
    return eficiencia_dias * eficiencia_temporal


# --- Función para construir cronograma ---
def construir_cronograma(dias, es_baseline=False):
    fechas = []
    calidades = []

    # Fechas de inicio y fin de cada fase
    fecha_uat_inicio = dt.datetime(2025, 7, 8)
    fecha_uat_fin = dt.datetime(2025, 7, 31)  # Fija

    fecha_mig_inicio = dt.datetime(2025, 8, 1)
    fecha_mig_fin = fecha_mig_inicio + timedelta(days=dias["Migration"])

    # E2E y Training dependen de Migration (habilitadas después)
    fecha_e2e_inicio = max(fecha_mig_fin, dt.datetime(2025, 9, 1))
    fecha_e2e_fin = fecha_e2e_inicio + timedelta(days=dias["E2E"])

    fecha_training_inicio = max(fecha_mig_fin, dt.datetime(2025, 10, 1))
    fecha_training_fin = fecha_training_inicio + timedelta(days=dias["Training"])

    # GoLive es fijo el 3 de noviembre
    fecha_golive = dt.datetime(2025, 11, 3)

    # Puntos de evaluación
    fechas = [
        fecha_uat_fin,
        fecha_mig_fin,
        fecha_e2e_fin,
        fecha_training_fin,
        fecha_golive,
    ]

    # Calcular delay en Migration
    delay_mig = max(0, (fecha_mig_fin - dt.datetime(2025, 8, 31)).days)

    # Calcular % de completitud para cada fase
    for i, fecha_eval in enumerate(fechas):
        # UAT: Completitud basada en eficiencia
        uat_pct = calcular_completitud_fase(dias["UAT"], baseline_days["UAT"])

        # Migration: Completitud con penalización SEVERA por delay (fase crítica)
        eficiencia_temporal_mig = max(
            0.5, 1.0 - (delay_mig * 0.05)
        )  # 5% penalización por día de delay
        migration_pct = calcular_completitud_fase(
            dias["Migration"], baseline_days["Migration"], eficiencia_temporal_mig
        )

        # E2E: Solo se habilita después de Migration
        if fecha_eval >= fecha_e2e_inicio:
            e2e_pct = calcular_completitud_fase(dias["E2E"], baseline_days["E2E"])
        else:
            e2e_pct = 0

        # Training: Solo se habilita después de Migration
        if fecha_eval >= fecha_training_inicio:
            training_pct = calcular_completitud_fase(
                dias["Training"], baseline_days["Training"]
            )
        else:
            training_pct = 0

        # Resources: Promedio ponderado de las fases principales
        resources_pct = (
            uat_pct * 0.2 + migration_pct * 0.4 + e2e_pct * 0.2 + training_pct * 0.2
        )

        # Hypercare: Solo activo después del Go-Live
        if fecha_eval >= fecha_golive:
            hypercare_pct = min(
                100, (fecha_eval - fecha_golive).days * 10
            )  # Crece gradualmente
        else:
            hypercare_pct = 0

        # Aplicar modelo econométrico
        calidad = quality_model_econometric(
            uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
        )
        calidades.append(calidad)

    return fechas, calidades, delay_mig


# --- Construir baseline y escenario ---
fechas_base, calidad_base, delay_base = construir_cronograma(
    baseline_days, es_baseline=True
)
fechas_esc, calidad_esc, delay_esc = construir_cronograma(dias_esc, es_baseline=False)

# --- Añadir punto de diciembre para Hypercare ---
fechas_base_extended = fechas_base + [dt.datetime(2025, 12, 3)]
# Para diciembre, Hypercare está al 100%
hypercare_dic = 100
calidad_dic_base = quality_model_econometric(100, 100, 100, 100, 100, hypercare_dic)
calidad_base_extended = calidad_base + [calidad_dic_base]

fechas_esc_extended = fechas_esc + [dt.datetime(2025, 12, 3)]
# Para escenario en diciembre, considerar impacto SEVERO del delay
eficiencia_temporal_dic = max(0.5, 1.0 - (delay_esc * 0.05))
migration_pct_dic = 100 * eficiencia_temporal_dic
calidad_dic_esc = quality_model_econometric(
    100, migration_pct_dic, 100, 100, 100, hypercare_dic
)
calidad_esc_extended = calidad_esc + [calidad_dic_esc]

# --- Gráfica temporal de calidad ---
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=fechas_base_extended,
        y=calidad_base_extended,
        mode="lines+markers",
        name="Baseline Quality (%)",
        line=dict(color="blue", width=3),
        marker=dict(size=8),
    )
)
fig.add_trace(
    go.Scatter(
        x=fechas_esc_extended,
        y=calidad_esc_extended,
        mode="lines+markers",
        name="Scenario Quality (%)",
        line=dict(color="orange", dash="dash", width=3),
        marker=dict(size=8),
    )
)

# Línea vertical en Go-Live (3 nov)
golive_date = dt.datetime(2025, 11, 3)
fig.add_shape(
    type="line",
    x0=golive_date,
    x1=golive_date,
    y0=0,
    y1=1,
    yref="paper",
    line=dict(color="red", width=2, dash="dot"),
)
fig.add_annotation(
    x=golive_date,
    y=1.02,
    yref="paper",
    text="Go-Live (3 Nov)",
    showarrow=False,
    font=dict(color="red"),
)

fig.update_layout(
    title="Modelo Econométrico Go-Live - Evolución de Calidad",
    xaxis_title="Fecha",
    yaxis_title="Quality (%)",
    yaxis=dict(range=[0, 100]),
    height=500,
    showlegend=True,
)
st.plotly_chart(fig, use_container_width=True)

# --- Métricas clave ---
st.subheader("Métricas del Modelo Econométrico")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Calidad Go-Live Baseline", f"{calidad_base[4]:.1f}%")
with col2:
    st.metric(
        "Calidad Go-Live Escenario",
        f"{calidad_esc[4]:.1f}%",
        delta=f"{calidad_esc[4] - calidad_base[4]:.1f}%",
    )
with col3:
    st.metric("Delay Migration", f"{delay_esc} días" if delay_esc > 0 else "Sin delay")
with col4:
    st.metric("Calidad Final (Dic)", f"{calidad_esc_extended[-1]:.1f}%")

# --- Tabla de evolución temporal ---
st.subheader("Evolución Temporal de Calidad")


def calcular_calidad_en_fecha(fecha_objetivo, fechas, calidades):
    for i, fecha in enumerate(fechas):
        if fecha >= fecha_objetivo:
            return calidades[i] if i < len(calidades) else calidades[-1]
    return calidades[-1] if calidades else 0


tabla_temporal = []
for fecha in fechas_clave:
    fila = {
        "Fecha": fecha.strftime("%Y-%m-%d"),
        "Baseline (%)": f"{calcular_calidad_en_fecha(fecha, fechas_base_extended, calidad_base_extended):.1f}",
        "Escenario (%)": f"{calcular_calidad_en_fecha(fecha, fechas_esc_extended, calidad_esc_extended):.1f}",
        "Diferencia (%)": f"{calcular_calidad_en_fecha(fecha, fechas_esc_extended, calidad_esc_extended) - calcular_calidad_en_fecha(fecha, fechas_base_extended, calidad_base_extended):.1f}",
    }
    tabla_temporal.append(fila)

df_temporal = pd.DataFrame(tabla_temporal)
st.dataframe(df_temporal, use_container_width=True)

# --- Análisis de sensibilidad ---
st.subheader("Análisis de Sensibilidad del Modelo")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Coeficientes Beta del Modelo Mejorado:**")
    st.markdown("- UAT: 0.25 (11.4% de impacto)")
    st.markdown("- Migration: 0.40 (18.2% de impacto) **CRÍTICA**")
    st.markdown("- E2E: 0.20 (9.1% de impacto)")
    st.markdown("- Training: 0.15 (6.8% de impacto)")
    st.markdown("- Resources: 0.10 (4.5% de impacto)")
    st.markdown("- Hypercare: 0.10 (4.5% de impacto)")

with col2:
    st.markdown("**Impacto CRÍTICO del Delay en Migration:**")
    st.markdown("- 5% de penalización por día de delay")
    st.markdown("- **BLOQUEA** E2E y Training si no está completa")
    st.markdown("- Reduce eficiencia de fases dependientes")
    st.markdown("- Impacto exponencial en calidad final")

# --- Mostrar fórmula del modelo ---
st.markdown("---")
st.subheader("Modelo Econométrico con Migration Crítica")
st.latex(
    r"Quality = \frac{1.00 + 0.25 \times UAT + 0.40 \times Migration + 0.20 \times E2E^* + 0.15 \times Training^* + 0.10 \times Resources + 0.10 \times Hypercare}{2.20} \times 100"
)

st.info(
    "**Nota:** Migration es la fase CRÍTICA con peso duplicado (0.40). E2E* y Training* se ven bloqueadas si Migration no está completa. El modelo penaliza severamente (5% por día) los delays en Migration. La calidad máxima es 100% con todas las fases perfectas."
)
