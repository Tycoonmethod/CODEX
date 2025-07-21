import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, date, time, timedelta
import traceback
from translations import TEXT, LANGUAGES
from styles import (
    COLORS,
    inject_custom_css,
    card,
    metric,
    phase_bar,
    toast,
    PLOT_LAYOUT,
)

# --- UI Configuration ---
st.set_page_config(page_title="Modelo Interactivo", layout="wide")


# --- Funciones helper y modelo econométrico ---

# Factores de penalización por día de retraso para cada fase
DELAY_PENALTY_FACTORS = {
    "UAT": 0.0125,       # 1.25%
    "Migration": 0.02,   # 2.0% (Crítica)
    "E2E": 0.01,         # 1.0%
    "Training": 0.0075,  # 0.75%
    "PRO": 0.005,        # 0.5%
    "Hypercare": 0.005   # 0.5%
}

def quality_model_econometric(params):
    """
    Modelo econométrico mejorado donde Migration es verdaderamente crítica
    """
    # Extraer porcentajes
    uat_pct = params["UAT"]
    migration_pct = params["Migration"]
    e2e_pct = params["E2E"]
    training_pct = params["Training"]
    pro_pct = params["PRO"]
    hypercare_pct = params["Hypercare"]

    # Migration como multiplicador crítico
    migration_factor = migration_pct

    # Si Migration no está completa, E2E y Training se ven severamente afectados
    if migration_pct < 1:
        # Factor de bloqueo: E2E y Training dependen críticamante de Migration
        bloqueo_factor = migration_factor * 0.6  # Reducción severa
        e2e_pct = e2e_pct * bloqueo_factor
        training_pct = training_pct * bloqueo_factor

    # Modelo con Migration como fase crítica (corregido para incluir PRO)
    valor_original = (
        1.00  # Intercepto reducido
        + 0.25 * uat_pct  # UAT: peso reducido
        + 0.40 * migration_pct  # Migration: peso DUPLICADO (crítica)
        + 0.20 * e2e_pct  # E2E: peso aumentado
        + 0.15 * training_pct  # Training: peso aumentado
        + 0.10 * pro_pct  # PRO: peso añadido
        + 0.10 * hypercare_pct  # Hypercare: peso reducido
    )

    # Factor de normalización: 1.00 + 0.25 + 0.40 + 0.20 + 0.15 + 0.10 + 0.10 = 2.20
    factor_normalizacion = 2.20

    # Calidad normalizada entre 0% y 100%
    calidad_normalizada = (valor_original / factor_normalizacion) * 100

    return min(max(calidad_normalizada, 0), 100)


def get_completion_pct(
    start: datetime, end: datetime, eval_date: datetime, baseline_duration: int = None
) -> float:
    """
    Devuelve el % completitud de una fase:
      - Si eval_date < start: 0%
      - Si start <= eval_date < end: progresión lineal
      - Si eval_date >= end:
          * Si baseline_duration None: 100%
          * Si actual_duration > baseline_duration:
                techo permanente = (baseline_duration / actual_duration) * 100
          * Sino: 100%
    """
    # Normalize inputs to datetime
    if start is None or end is None or eval_date is None:
        return 0.0
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d")
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d")
    if isinstance(eval_date, str):
        eval_date = datetime.strptime(eval_date, "%Y-%m-%d")
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, time.min)
    if isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, time.min)
    if isinstance(eval_date, date) and not isinstance(eval_date, datetime):
        eval_date = datetime.combine(eval_date, time.min)

    if eval_date < start:
        return 0.0

    actual = (end - start).days
    if actual <= 0:
        return 100.0

    # Dentro del periodo
    if eval_date < end:
        pct = ((eval_date - start).days / actual) * 100
    else:
        # Tras el fin real
        if baseline_duration and actual > baseline_duration:
            pct = (baseline_duration / actual) * 100
        else:
            pct = 100.0

    # Aplica siempre el techo en el tramo de ejecución
    if baseline_duration and actual > baseline_duration:
        pct = min(pct, (baseline_duration / actual) * 100)

    return max(0.0, min(100.0, pct))


def to_dt(x):
    """Convierte date o datetime.date en datetime.datetime a las 00:00h"""
    if x is None:
        return datetime.now()  # Valor por defecto en lugar de None
    if isinstance(x, datetime):
        return x
    if isinstance(x, date) and not isinstance(x, datetime):
        return datetime.combine(x, time.min)
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x)
    return x


def get_days_between(start_date, end_date):
    """Calcula los días entre dos fechas, manejando None"""
    if start_date is None or end_date is None:
        return 0
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, time.min)
    if isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, time.min)
    return (end_date - start_date).days


def add_days(base_date, days):
    """Añade días a una fecha, manejando None"""
    if base_date is None:
        return datetime.now()
    if isinstance(base_date, str):
        base_date = datetime.strptime(base_date, "%Y-%m-%d")
    if isinstance(base_date, date) and not isinstance(base_date, datetime):
        base_date = datetime.combine(base_date, time.min)
    return base_date + timedelta(days=days)


def construir_cronograma_seguro(sim_windows, penalty_baseline=None):
    """
    Construye el cronograma extendiendo el horizonte temporal para encontrar la calidad objetivo.
    """
    try:
        effective_windows = {k: v for k, v in sim_windows.items()}

        # Propagar delays en cascada, ya que es la mecánica del proyecto.
        dependencies = {
            "Migration": "UAT", "E2E": "Migration", "Training": "E2E",
            "PRO": "E2E", "Hypercare": "PRO"
        }
        for phase, predecessor in dependencies.items():
            predecessor_end = effective_windows[predecessor][1]
            intended_start = effective_windows[phase][0]
            actual_start = max(intended_start, predecessor_end + timedelta(days=1))
            duration = (effective_windows[phase][1] - intended_start).days
            actual_end = actual_start + timedelta(days=duration)
            effective_windows[phase] = (actual_start, actual_end)

        # Calcular delays y penalizaciones SOLO si se proporciona un baseline.
        delays = {}
        penalty_factors = {fase: 1.0 for fase in baseline_windows.keys()}

        if penalty_baseline:
            delays = {fase: max(0, (effective_windows[fase][1] - penalty_baseline[fase][1]).days)
                      for fase in baseline_windows.keys()}
            penalty_factors = {fase: 1 - (delay * DELAY_PENALTY_FACTORS.get(fase, 0))
                               for fase, delay in delays.items()}

        # Extender el horizonte temporal para la simulación
        start_date = min(effective_windows['UAT'][0], baseline_windows['UAT'][0])
        last_phase_end = max(effective_windows['Hypercare'][1], baseline_windows['Hypercare'][1])
        # Añadir un buffer de 6 meses para asegurar que encontramos la fecha objetivo
        end_date = last_phase_end + timedelta(days=180)
        fechas_evaluacion = pd.date_range(start=start_date, end=end_date, freq='D')

        calidades = []
        for fecha in fechas_evaluacion:
            params = {}
            for fase in baseline_windows.keys():
                pct = get_completion_pct(
                    effective_windows[fase][0], effective_windows[fase][1], fecha,
                    baseline_duration=baseline_days.get(fase)
                )
                params[fase] = (pct / 100) * penalty_factors[fase]

            calidad = quality_model_econometric(params)
            calidades.append(calidad)

        end_dates = {fase: effective_windows[fase][1] for fase in baseline_windows}
        return fechas_evaluacion, calidades, delays, end_dates

    except Exception as e:
        st.error(f"Error en construir_cronograma_seguro: {type(e).__name__}: {e}")
        st.error(f"Traceback completo: {traceback.format_exc()}")
        return [], [], {}, {}


# Rango global donde pueden moverse los sliders
CAL_START = datetime(2025, 7, 1)
CAL_END = datetime(2026, 1, 1)

# Baselines fijos de cada fase
baseline_windows = {
    "UAT": (datetime(2025, 7, 8), datetime(2025, 7, 31)),
    "Migration": (datetime(2025, 8, 1), datetime(2025, 8, 31)),
    "E2E": (datetime(2025, 9, 1), datetime(2025, 9, 30)),
    "Training": (datetime(2025, 10, 1), datetime(2025, 10, 31)),
    "PRO": (datetime(2025, 10, 1), datetime(2025, 10, 30)),
    "Hypercare": (datetime(2025, 11, 3), datetime(2025, 12, 3)),
}

# Baseline durations for preventing reabsorption
baseline_days = {
    "UAT": 23,  # 8-Jul to 31-Jul
    "Migration": 30,  # 1-Aug to 31-Aug
    "E2E": 29,  # 1-Sep to 30-Sep
    "Training": 30,  # 1-Oct to 31-Oct
    "PRO": 29,  # 1-Oct to 30-Oct
    "Hypercare": 30,  # 3-Nov to 3-Dec
}

# Inject custom CSS
inject_custom_css()

# Estilos consistentes para modo claro/oscuro
st.markdown(
    """
<style>
[data-theme="light"] .stMetric {
    background-color: #1f4e78 !important;
    color: white !important;
}
[data-theme="light"] .stTable td, .stTable th {
    color: white !important;
}
[data-theme="light"] .stSidebar {
    background-color: #0d274e !important;
    color: white !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# --- State Initialization (Robust, In-Page) ---
def initialize_state():
    today = datetime.combine(datetime.now().date(), time.min)
    migration_end = datetime(2025, 8, 31)
    migration_duration = (migration_end - today).days

    defaults = {
        "lang": "es",
        "project_name": "Proyecto Go-Live 2025",
        "sponsor": "CEO",
        "budget_total": 2000000,
        "budget_used": 75,
        "team_size": 25,
        "uat_start": datetime(2025, 7, 8),
        "uat_end": datetime(2025, 7, 31),
        "migration_start": today,
        "migration_end": migration_end,
        "e2e_start": datetime(2025, 9, 1),
        "e2e_end": datetime(2025, 9, 30),
        "training_start": datetime(2025, 10, 1),
        "training_end": datetime(2025, 10, 31),
        "pro_start": datetime(2025, 10, 15),
        "pro_end": datetime(2025, 10, 28),
        "hypercare_start": datetime(2025, 10, 29),
        "hypercare_end": datetime(2025, 11, 28),
        "golive_days": 6,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()

# --------------------------------------------------
# Asegurar que 'lang' siempre está definido
# --------------------------------------------------
# Si no existe, lo inicializamos a 'es' por defecto
if "lang" not in st.session_state:
    st.session_state.lang = "es"

# Ahora creamos la variable local que usan tus textos
lang = st.session_state.lang

# --- UI ---
# Create a container for the main content
main_container = st.container()

# Sidebar with collapsible configuration
with st.sidebar:
    # Botón Reset para restaurar valores baseline
    if st.button("🔄 Reset a Baseline", use_container_width=True, type="secondary"):
        # Resetear todos los sliders a sus valores baseline
        for fase in baseline_windows.keys():
            if f"slider_{fase}" in st.session_state:
                del st.session_state[f"slider_{fase}"]
        # Limpiar también la fecha de Go-Live sugerida
        if 'suggested_golive_date' in st.session_state:
            del st.session_state.suggested_golive_date
        st.rerun()

    st.header("Configuración de Fases")
    scenario_windows = {}
    for fase, (b_start, b_end) in baseline_windows.items():
        lbl = f"{fase} (Baseline: {b_start.strftime('%d-%b')} → {b_end.strftime('%d-%b')})"
        start, end = st.slider(
            lbl,
            min_value=CAL_START,
            max_value=CAL_END,
            value=(b_start, b_end),
            format="YYYY-MM-DD",
            key=f"slider_{fase}",
        )
        scenario_windows[fase] = (start, end)

# Desempaquetar fechas de escenario
uat_start, uat_end = scenario_windows["UAT"]
mig_start, mig_end = scenario_windows["Migration"]
e2e_start, e2e_end = scenario_windows["E2E"]
train_start, train_end = scenario_windows["Training"]
pro_start, pro_end = scenario_windows["PRO"]
hyper_start, hyper_end = scenario_windows["Hypercare"]

# --- Definición de fechas baseline ---
baseline_start_dates = {
    "UAT": datetime(2025, 7, 8),
    "Migration": datetime(2025, 8, 1),
    "E2E": datetime(2025, 9, 1),
    "Training": datetime(2025, 10, 1),
    "PRO": datetime(2025, 10, 1),
    "Hypercare": datetime(2025, 11, 3),
}

baseline_end_dates = {
    "UAT": datetime(2025, 7, 31),
    "Migration": datetime(2025, 8, 31),
    "E2E": datetime(2025, 9, 30),
    "Training": datetime(2025, 10, 31),
    "PRO": datetime(2025, 10, 30),
    "Hypercare": datetime(2025, 12, 3),
}

# Fechas baseline por fase
baseline_ranges = {
    "UAT": {
        "start": datetime(2025, 7, 8),
        "end": datetime(2025, 7, 31),
        "label": "UAT (Baseline: 8-Jul → 31-Jul)",
    },
    "Migration": {
        "start": datetime(2025, 8, 1),
        "end": datetime(2025, 8, 31),
        "label": "Migration (Baseline: 1-Ago → 31-Ago)",
    },
    "E2E": {
        "start": datetime(2025, 9, 1),
        "end": datetime(2025, 9, 30),
        "label": "E2E (Baseline: 1-Sep → 30-Sep)",
    },
    "Training": {
        "start": datetime(2025, 10, 1),
        "end": datetime(2025, 10, 31),
        "label": "Training (Baseline: 1-Oct → 31-Oct)",
    },
    "PRO": {
        "start": datetime(2025, 10, 1),
        "end": datetime(2025, 10, 30),
        "label": "PRO (Baseline: 1-Oct → 30-Oct)",
    },
    "Hypercare": {
        "start": datetime(2025, 11, 4),
        "end": datetime(2025, 12, 3),
        "label": "Hypercare (Baseline: 4-Nov → 3-Dic)",
    },
}

# Fechas deadline por fase
baseline_fechas = {
    "UAT": datetime(2025, 7, 31),
    "Migration": datetime(2025, 8, 31),
    "E2E": datetime(2025, 9, 30),
    "Training": datetime(2025, 10, 31),
    "PRO": datetime(2025, 10, 30),
    "Hypercare": datetime(2025, 11, 28),
    "GoLive": datetime(2025, 11, 3),
}

# Construir cronograma baseline (sin penalizaciones)
fechas_base, calidad_base, _, _ = construir_cronograma_seguro(
    sim_windows=baseline_windows
)

# Construir cronograma escenario (con penalizaciones contra el baseline)
fechas_esc, calidad_esc, delays_esc, end_dates_esc = construir_cronograma_seguro(
    sim_windows=scenario_windows, 
    penalty_baseline=baseline_windows
)

# --- PUNTO: interpolar calidad en Go-Live ---
go_live_date = datetime(2025, 11, 3)

# Convertir a timestamps
base_ts = [f.timestamp() for f in fechas_base]
esc_ts = [f.timestamp() for f in fechas_esc]

# Interpolación
calidad_base_gl = np.interp(go_live_date.timestamp(), base_ts, calidad_base)
calidad_esc_gl = np.interp(go_live_date.timestamp(), esc_ts, calidad_esc)
delta_gl = calidad_esc_gl - calidad_base_gl

# Countdown hasta Go-Live
dias_para_golive = max(
    0, (to_dt(datetime(2025, 11, 3)) - to_dt(datetime.now().date())).days
)

# Main content area with cards
with main_container:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.title(TEXT[lang]["page1_name"])
        st.info(f"🔔 La calidad en Go-Live baja de {calidad_base_gl:.1f}% a {calidad_esc_gl:.1f}% (Δ {delta_gl:+.1f}%)")
        st.markdown(card("📈 Evolución de Calidad", ""), unsafe_allow_html=True)
    
    with col2:
        # Tabla de Análisis de Impactos
        rows = []
        for fase, delay_days in delays_esc.items():
            if delay_days > 0:
                penalty_factor = DELAY_PENALTY_FACTORS.get(fase, 0)
                quality_loss = delay_days * penalty_factor * 100
                impact = "Alto 🔴" if quality_loss > 10 else "Medio 🟡" if quality_loss > 0 else "Ninguno 🟢"
                rows.append({
                    "Fase": fase, 
                    "Retraso (días)": delay_days, 
                    "Pérdida Calidad (%)": f"{quality_loss:.2f}",
                    "Impacto": impact
                })
        
        if rows:
            df_retrasos = pd.DataFrame(rows)
            # Usar st.dataframe para una tabla nativa y más limpia
            st.markdown("##### ⚠️ Análisis de Impactos")
            st.dataframe(df_retrasos, use_container_width=True)

        # Nueva tabla de desglose de penalizaciones
        st.markdown("##### 🔍 Desglose de Penalización")
        penalty_rows = []
        for fase, factor in DELAY_PENALTY_FACTORS.items():
            delay = delays_esc.get(fase, 0)
            total_impact = delay * factor * 100
            penalty_rows.append({
                "Fase": fase,
                "Penalización Diaria (%)": f"{factor * 100:.2f}",
                "Impacto Total (%)": f"{total_impact:.2f}"
            })
        df_penalties = pd.DataFrame(penalty_rows)
        st.dataframe(df_penalties, use_container_width=True)
        
    # Create the plot with enhanced styling
    fig = go.Figure()

    # Add baseline trace
    fig.add_trace(
        go.Scatter(
            x=[d.strftime("%Y-%m-%d") for d in fechas_base],
            y=calidad_base,
            name="Baseline",
            line=dict(color=COLORS["baseline"], width=2),
            hovertemplate="%{y:.1f}%<extra>Baseline</extra>",
        )
    )

    # Add scenario trace
    fig.add_trace(
        go.Scatter(
            x=[d.strftime("%Y-%m-%d") for d in fechas_esc],
            y=calidad_esc,
            name="Escenario",
            line=dict(color=COLORS["scenario"], width=2),
            hovertemplate="%{y:.1f}%<extra>Escenario</extra>",
        )
    )

    # Add phase lines
    for fase, (start, end) in scenario_windows.items():
        # Línea vertical para cada fase
        fig.add_shape(
            type="line",
            x0=start.strftime("%Y-%m-%d"),
            x1=start.strftime("%Y-%m-%d"),
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(color=COLORS["phases"], width=1, dash="dash"),
        )
        # Etiqueta para cada fase
        fig.add_annotation(
            x=start.strftime("%Y-%m-%d"),
            y=1.02,
            xref="x",
            yref="paper",
            text=f"<b>{fase}</b>",
            showarrow=False,
            font=dict(size=12, color=COLORS["phases"]),
            bgcolor="rgba(49,51,63,0.7)",
            bordercolor=COLORS["phases"],
            borderwidth=1,
        )

    # Add go-live line (original)
    golive_date = baseline_fechas["GoLive"]
    fig.add_shape(
        type="line",
        x0=golive_date.strftime("%Y-%m-%d"),
        x1=golive_date.strftime("%Y-%m-%d"),
        y0=0, y1=1, xref="x", yref="paper",
        line=dict(color=COLORS["golive"], width=4, dash="solid"),
    )
    fig.add_annotation(
        x=golive_date.strftime("%Y-%m-%d"), y=1.02, xref="x", yref="paper",
        text="<b>GO-LIVE ORIGINAL</b>", showarrow=False,
        font=dict(size=14, color=COLORS["golive"]),
        bgcolor="rgba(49,51,63,0.7)", bordercolor=COLORS["golive"], borderwidth=1,
    )

    # Añadir la línea del Go-Live SUGERIDO si existe
    if 'suggested_golive_date' in st.session_state:
        suggested_date = st.session_state.suggested_golive_date
        fig.add_shape(
            type="line",
            x0=suggested_date.strftime("%Y-%m-%d"),
            x1=suggested_date.strftime("%Y-%m-%d"),
            y0=0, y1=1, xref="x", yref="paper",
            line=dict(color=COLORS["success"], width=3, dash="dashdot"),
        )
        fig.add_annotation(
            x=suggested_date.strftime("%Y-%m-%d"), y=0.95, xref="x", yref="paper",
            text="<b>GO-LIVE SUGERIDO</b>", showarrow=True, arrowhead=2, ax=0, ay=-40,
            font=dict(size=14, color=COLORS["success"]),
            bgcolor="rgba(49,51,63,0.7)", bordercolor=COLORS["success"], borderwidth=1,
        )

    # Update layout with unified axis configuration
    # Determinar el rango dinámico del eje X
    x_axis_end = baseline_windows['Hypercare'][1] + timedelta(days=30)
    if 'suggested_golive_date' in st.session_state:
        x_axis_end = max(x_axis_end, st.session_state.suggested_golive_date + timedelta(days=30))

    fig.update_layout(
        title=dict(text="Evolución de Calidad Go-Live", font=dict(size=20)),
        xaxis=dict(
            title="Fecha",
            type="date",
            range=[
                (baseline_windows['UAT'][0] - timedelta(days=15)).strftime("%Y-%m-%d"),
                x_axis_end.strftime("%Y-%m-%d"),
            ],
            tickformat="%b %Y",
            gridcolor="rgba(255,255,255,0.1)",
            zerolinecolor="rgba(255,255,255,0.2)",
        ),
        yaxis=dict(
            title="Calidad (%)",
            range=[40, 105],
            gridcolor="rgba(255,255,255,0.1)",
            zerolinecolor="rgba(255,255,255,0.2)",
        ),
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=40, r=40, t=80, b=40),
        height=600,
        showlegend=True,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Estado de fases en sidebar
st.sidebar.subheader("Estado de Fases")

# Ajustar el widget lateral de "Calidad Actual"
st.sidebar.subheader("Calidad Escenario (Go-Live)")
st.sidebar.write(f"{calidad_esc_gl:.1f}%")

baseline_days = {
    "UAT": (baseline_windows["UAT"][1] - baseline_windows["UAT"][0]).days,
    "Migration": (
        baseline_windows["Migration"][1] - baseline_windows["Migration"][0]
    ).days,
    "E2E": (baseline_windows["E2E"][1] - baseline_windows["E2E"][0]).days,
    "Training": (
        baseline_windows["Training"][1] - baseline_windows["Training"][0]
    ).days,
    "PRO": (baseline_windows["PRO"][1] - baseline_windows["PRO"][0]).days,
    "Hypercare": (
        baseline_windows["Hypercare"][1] - baseline_windows["Hypercare"][0]
    ).days,
}

for fase, delay in delays_esc.items():
    if fase == "PRO":
        # ✅ PRO: calcular delay directamente del slider
        pro_delay = max(
            0, (scenario_windows["PRO"][1] - baseline_windows["PRO"][1]).days
        )
        if pro_delay == 0:
            st.sidebar.success("✅ PRO: En plazo")
        else:
            st.sidebar.error(f"🚨 PRO: {pro_delay} días de retraso")
    else:
        if delay == 0:
            # dentro de rango: barra verde
            st.sidebar.progress(1.0, text=f"{fase}: En plazo")
        elif delay <= baseline_days[fase]:
            # retraso pero aún dentro de margen
            st.sidebar.progress(
                (baseline_days[fase] - delay) / baseline_days[fase],
                text=f"{fase}: {delay} días de retraso",
            )
        else:
            # fuera de rango
            st.sidebar.error(f"{fase}: Fase fuera de rango")

# Show toast notifications for significant changes
if "previous_quality" not in st.session_state:
    st.session_state.previous_quality = calidad_esc_gl

quality_change = calidad_esc_gl - st.session_state.previous_quality
if abs(quality_change) >= 1:
    message = f"Calidad {'mejorada' if quality_change > 0 else 'reducida'} en {abs(quality_change):.1f}%"
    st.markdown(
        toast(message, "success" if quality_change > 0 else "warning"),
        unsafe_allow_html=True,
    )

st.session_state.previous_quality = calidad_esc_gl

# --- Fórmula del Modelo ---
st.subheader("Modelo Econométrico con Migration Crítica")
st.latex(
    r"Quality = \frac{1.00 + 0.25 \times UAT + 0.40 \times Migration + 0.20 \times E2E^* + 0.15 \times Training^* + 0.10 \times PRO + 0.10 \times Hypercare}{2.20} \times 100"
)
st.info(
    "**Nota:** Migration es la fase CRÍTICA con peso duplicado (0.40). Los delays se propagan en cadena afectando a todas las fases posteriores."
)

with st.sidebar:
    st.header("Análisis Predictivo")
    st.markdown("---")

    # --- Sección 1: Análisis del Escenario Actual ---
    st.subheader("1. Predecir con Plan Actual")
    st.info("Calcula cuándo se alcanzará la calidad si se mantiene el plan actual, con todas sus penalizaciones por retraso.")
    
    current_target_quality = st.number_input(
        "Calidad Objetivo en Plan Actual (%)", 
        min_value=0.0, max_value=100.0, value=90.0, step=0.5,
        key="current_target_quality"
    )

    if st.button("Calcular Fecha con Plan Actual"):
        if 'calidad_esc' in locals() and 'fechas_esc' in locals() and len(calidad_esc) > 0:
            quality_array = np.array(calidad_esc)
            indices = np.where(quality_array >= current_target_quality)[0]
            if indices.size > 0:
                st.success(f"✅ Objetivo alcanzado el: **{fechas_esc[indices[0]].strftime('%d-%b-%Y')}**")
            else:
                st.warning(f"⚠️ Objetivo no alcanzado. Calidad máx: **{quality_array[-1]:.1f}%**.")
        else:
            st.error("Error: Datos del escenario no calculados.")

    st.markdown("---")

    # --- Sección 2: Propuesta de Nuevo Go-Live ---
    st.subheader("2. Proponer Nueva Fecha de Go-Live")
    st.info("Calcula una nueva fecha de Go-Live para alcanzar tu objetivo, usando el plan actual como la nueva referencia sin penalizaciones.")
    
    new_plan_target_quality = st.number_input(
        "Calidad Objetivo para Nuevo Plan (%)", 
        min_value=0.0, max_value=100.0, value=95.0, step=0.5,
        key="new_plan_target_quality"
    )

    if st.button("Sugerir Nueva Fecha de Go-Live"):
        # Simular un escenario ideal usando las fechas del escenario actual
        fechas_ideal, calidad_ideal, _, _ = construir_cronograma_seguro(sim_windows=scenario_windows)
        
        if len(calidad_ideal) > 0:
            quality_array = np.array(calidad_ideal)
            indices = np.where(quality_array >= new_plan_target_quality)[0]
            
            if indices.size > 0:
                new_golive_date = fechas_ideal[indices[0]]
                # Guardar la fecha sugerida en el estado de la sesión para que el gráfico la pueda usar
                st.session_state.suggested_golive_date = new_golive_date
                st.success(f"💡 **Fecha sugerida: {new_golive_date.strftime('%d-%b-%Y')}** (visualizada en el gráfico)")
            else:
                max_quality = quality_array[-1]
                # Si no se encuentra, limpiar la fecha sugerida anterior
                if 'suggested_golive_date' in st.session_state:
                    del st.session_state.suggested_golive_date
                st.error(f"❌ Imposible alcanzar. La calidad máxima del nuevo plan sería de **{max_quality:.1f}%**.")
        else:
            st.error("Error: No se pudo simular el nuevo plan.")
