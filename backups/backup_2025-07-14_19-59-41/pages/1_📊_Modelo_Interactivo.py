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
    resources_pct = params["Resources"]
    hypercare_pct = params["Hypercare"]

    # Migration como multiplicador crítico
    migration_factor = migration_pct

    # Si Migration no está completa, E2E y Training se ven severamente afectados
    if migration_pct < 1:
        # Factor de bloqueo: E2E y Training dependen críticamante de Migration
        bloqueo_factor = migration_factor * 0.6  # Reducción severa
        e2e_pct = e2e_pct * bloqueo_factor
        training_pct = training_pct * bloqueo_factor

    # Modelo con Migration como fase crítica
    valor_original = (
        1.00  # Intercepto reducido
        + 0.25 * uat_pct  # UAT: peso reducido
        + 0.40 * migration_pct  # Migration: peso DUPLICADO (crítica)
        + 0.20 * e2e_pct  # E2E: peso aumentado
        + 0.15 * training_pct  # Training: peso aumentado
        + 0.10 * resources_pct  # Resources: igual
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


def construir_cronograma_seguro(scenario_windows, es_baseline=False):
    """
    Construye el cronograma usando las fechas de los sliders y propagando delays en cadena.
    Incluye el impacto de PRO en Go-Live y Hypercare en el periodo posterior.
    """
    try:
        if es_baseline:
            # Para baseline, usamos fechas fijas sin delays
            start_date = baseline_windows["UAT"][0]
            end_date = baseline_windows["Hypercare"][1]
            days_range = (end_date - start_date).days + 1
            fechas_evaluacion = [
                start_date + timedelta(days=i) for i in range(days_range)
            ]

            calidades = []
            golive_date = datetime(2025, 11, 3)

            for fecha in fechas_evaluacion:
                uat_pct = get_completion_pct(
                    baseline_windows["UAT"][0], baseline_windows["UAT"][1], fecha
                )
                mig_pct = get_completion_pct(
                    baseline_windows["Migration"][0],
                    baseline_windows["Migration"][1],
                    fecha,
                )
                e2e_pct = get_completion_pct(
                    baseline_windows["E2E"][0], baseline_windows["E2E"][1], fecha
                )
                train_pct = get_completion_pct(
                    baseline_windows["Training"][0],
                    baseline_windows["Training"][1],
                    fecha,
                )
                pro_pct = get_completion_pct(
                    baseline_windows["PRO"][0], baseline_windows["PRO"][1], fecha
                )
                # Hypercare solo afecta después del Go-Live
                hyper_pct = 0
                if fecha >= baseline_windows["Hypercare"][0]:
                    hyper_pct = get_completion_pct(
                        baseline_windows["Hypercare"][0],
                        baseline_windows["Hypercare"][1],
                        fecha,
                    )

                calidad = quality_model_econometric(
                    {
                        "UAT": uat_pct / 100,
                        "Migration": mig_pct / 100,
                        "E2E": e2e_pct / 100,
                        "Training": train_pct / 100,
                        "PRO": pro_pct / 100,
                        "Resources": 0,
                        "Hypercare": hyper_pct / 100,
                    }
                )
                calidades.append(calidad)

            # Recopilar fechas finales baseline
            end_dates = {fase: baseline_windows[fase][1] for fase in baseline_windows}

            return fechas_evaluacion, calidades, {}, end_dates

        else:
            # 1) Extraemos los start/end de cada fase desde el scenario_windows
            uat_start, uat_end = scenario_windows["UAT"]
            mig_start, mig_end = scenario_windows["Migration"]
            e2e_start0, e2e_end0 = scenario_windows["E2E"]
            train_start0, train_end0 = scenario_windows["Training"]
            pro_start0, pro_end0 = scenario_windows["PRO"]
            hyper_start0, hyper_end0 = scenario_windows["Hypercare"]

            # 2) Deadlines y fechas clave
            dl = {fase: baseline_windows[fase][1] for fase in baseline_windows}
            golive_date = datetime(2025, 11, 3)

            # 3) Calculamos delay & desplazamos fases en cadena
            delays = {}

            # Migration
            delay_mig = max(0, (mig_end - dl["Migration"]).days)
            delays["Migration"] = delay_mig

            # E2E arranca tras mig_end + delay_mig
            e2e_start = mig_end + timedelta(days=delay_mig)
            e2e_end = e2e_start + timedelta(days=(e2e_end0 - e2e_start0).days)
            delay_e2e = max(0, (e2e_end - dl["E2E"]).days)
            delays["E2E"] = delay_mig + delay_e2e

            # Training arranca tras e2e_end + delay_e2e
            train_start = e2e_end + timedelta(days=delay_e2e)
            train_end = train_start + timedelta(days=(train_end0 - train_start0).days)
            delay_train = max(0, (train_end - dl["Training"]).days)
            delays["Training"] = delays["E2E"] + delay_train

            # PRO: idéntico a Training
            pro_start, pro_end = scenario_windows["PRO"]

            # Hypercare arranca tras Go-Live
            hyper_start = golive_date
            hyper_end = hyper_start + timedelta(days=(hyper_end0 - hyper_start0).days)
            delay_hyper = max(0, (hyper_end - dl["Hypercare"]).days)

            # 4) Construimos el timeline de evaluación a diario
            start = uat_start
            end = hyper_end
            days_range = (end - start).days + 1
            fechas_evaluacion = [start + timedelta(days=i) for i in range(days_range)]

            # 5) Para cada fecha, recalculamos pct completitud con los nuevos start/end
            calidades = []
            for fecha in fechas_evaluacion:
                # ✅ Todas las fases usan baseline_duration para evitar reabsorción
                uat_pct = get_completion_pct(
                    uat_start, uat_end, fecha, baseline_days["UAT"]
                )
                mig_pct = get_completion_pct(
                    mig_start, mig_end, fecha, baseline_days["Migration"]
                )
                e2e_pct = get_completion_pct(
                    e2e_start, e2e_end, fecha, baseline_days["E2E"]
                )

                # ✅ Training usa directamente el slider (no la cascada) con baseline duration
                train_pct = get_completion_pct(
                    train_start0,
                    train_end0,
                    fecha,
                    baseline_duration=baseline_days["Training"],
                )

                # ✅ PRO usa directamente el slider (no la cascada) con baseline duration
                pro_pct = get_completion_pct(
                    pro_start, pro_end, fecha, baseline_duration=baseline_days["PRO"]
                )

                # Hypercare solo afecta después del Go-Live con baseline duration
                hyper_pct = 0
                if fecha >= hyper_start0:
                    hyper_pct = get_completion_pct(
                        hyper_start0, hyper_end0, fecha, baseline_days["Hypercare"]
                    )

                # bloqueo crítico de Migration
                if mig_pct < 100:
                    block = (mig_pct / 100) * 0.6
                    e2e_pct *= block
                    train_pct *= block

                calidad = quality_model_econometric(
                    {
                        "UAT": uat_pct / 100,
                        "Migration": mig_pct / 100,
                        "E2E": e2e_pct / 100,
                        "Training": train_pct / 100,  # <— ahora dinámico del slider
                        "PRO": pro_pct / 100,  # <— ahora dinámico del slider
                        "Resources": 0,
                        "Hypercare": hyper_pct / 100,
                    }
                )
                calidades.append(calidad)

            # Recopilar fechas finales reales
            end_dates = {
                "UAT": uat_end,
                "Migration": mig_end,
                "E2E": e2e_end,
                "Training": train_end,
                # ✅ PRO y Hypercare usan directamente el slider
                "PRO": pro_end,
                "Hypercare": hyper_end0,
            }

            # --------------------------------------------------
            #  Cálculo de delays en cascada respecto al baseline
            # --------------------------------------------------
            delays = {}
            cum = 0
            for fase in ["UAT", "Migration", "E2E", "Training", "PRO", "Hypercare"]:
                real_end = scenario_windows[fase][1]
                base_end = baseline_windows[fase][1]
                this_delay = max(0, (real_end - base_end).days)
                if fase == "PRO":
                    # PRO delay = 0 dentro del baseline
                    delays[fase] = this_delay
                else:
                    cum += this_delay
                    delays[fase] = cum

            # Devolver también delays
            return fechas_evaluacion, calidades, delays, end_dates

    except Exception as e:
        st.error(f"Error en construir_cronograma_seguro: {type(e).__name__}: {e}")
        st.error(f"Traceback completo: {traceback.format_exc()}")
        return None, None, None, None


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

# Construir cronograma baseline
fechas_base, calidad_base, delays_base, end_dates_base = construir_cronograma_seguro(
    baseline_windows, es_baseline=True
)

# Construir cronograma escenario
fechas_esc, calidad_esc, delays_esc, end_dates_esc = construir_cronograma_seguro(
    scenario_windows, es_baseline=False
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
    st.title(TEXT[lang]["page1_name"])

    # Refrescar el mensaje superior de "Δ Calidad"
    st.info(
        f"🔔 La calidad en Go-Live baja de {calidad_base_gl:.1f}% a {calidad_esc_gl:.1f}% (Δ {delta_gl:+.1f}%)"
    )

    # Actualizar el panel "Impacto en Calidad" (Dashboard)
    st.subheader("Impacto en Calidad")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Calidad Baseline (Go-Live)", f"{calidad_base_gl:.1f}%")
    with col2:
        st.metric(
            "Calidad Escenario (Go-Live)",
            f"{calidad_esc_gl:.1f}%",
            delta=f"{delta_gl:.1f}%",
        )

    # Top row with KPI cards
    col1, col2, col3 = st.columns(3)

    with col1:
        # Go-Live Date Card
        golive_content = metric("Fecha Go-Live", "3 Nov 2025") + metric(
            "Días Restantes", f"{dias_para_golive}"
        )
        st.markdown(card("🚀 Go-Live", golive_content), unsafe_allow_html=True)

    with col2:
        # Phase Status Card
        phase_content = ""
        for fase in ["UAT", "Migration", "E2E", "Training", "PRO"]:
            delay = max(0, (scenario_windows[fase][1] - baseline_windows[fase][1]).days)
            color = COLORS["success"] if delay == 0 else COLORS["danger"]
            percentage = min(
                100, max(0, 100 - (delay * 5))
            )  # 5% penalty per day of delay
            phase_content += phase_bar(fase, percentage, color)
        st.markdown(card("📋 Estado de Fases", phase_content), unsafe_allow_html=True)

    # Quality Evolution Plot Card
    st.markdown(card("📈 Evolución de Calidad", ""), unsafe_allow_html=True)

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

    # Add go-live line
    golive_date = baseline_fechas["GoLive"]
    fig.add_shape(
        type="line",
        x0=golive_date.strftime("%Y-%m-%d"),
        x1=golive_date.strftime("%Y-%m-%d"),
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line=dict(color=COLORS["golive"], width=4, dash="solid"),
    )

    fig.add_annotation(
        x=golive_date.strftime("%Y-%m-%d"),
        y=1.02,
        xref="x",
        yref="paper",
        text="<b>GO-LIVE</b>",
        showarrow=False,
        font=dict(size=16, color=COLORS["golive"]),
        bgcolor="rgba(49,51,63,0.7)",
        bordercolor=COLORS["golive"],
        borderwidth=1,
    )

    # Update layout with unified axis configuration
    fig.update_layout(
        title=dict(text="Evolución de Calidad Go-Live", font=dict(size=20)),
        xaxis=dict(
            title="Fecha",
            type="date",
            range=[
                datetime(2025, 7, 1).strftime("%Y-%m-%d"),
                datetime(2025, 12, 31).strftime("%Y-%m-%d"),
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

    # Delays Table Card
    if delays_esc:  # Check if delays_esc is not empty
        rows = []
        for fase in ["Migration", "E2E", "Training", "PRO", "Hypercare"]:
            if fase == "PRO":
                # ✅ PRO: usar delay directo del slider
                end_real = scenario_windows["PRO"][1]
                end_base = baseline_windows["PRO"][1]
                delay = max(0, (end_real - end_base).days)
            else:
                end_real = end_dates_esc[fase]
                end_base = baseline_windows[fase][1]
                delay = max(0, (end_real - end_base).days)

            impact = (
                "Alto 🔴" if delay > 5 else "Medio 🟡" if delay > 0 else "Ninguno 🟢"
            )
            rows.append({"Fase": fase, "Retraso (días)": delay, "Impacto": impact})
        df_retrasos = pd.DataFrame(rows)

        delay_content = "<div id='analisis-retrasos' style='overflow-x: auto;'><table style='width: 100%; color: #ffffff;'>"
        delay_content += "<thead><tr><th style='color: #ffffff;'>Fase</th><th style='color: #ffffff;'>Retraso (días)</th><th style='color: #ffffff;'>Impacto</th></tr></thead>"
        delay_content += "<tbody>"
        for _, row in df_retrasos.iterrows():
            delay_content += f"<tr><td style='color: #ffffff;'>{row['Fase']}</td><td style='color: #ffffff;'>{row['Retraso (días)']}</td><td style='color: #ffffff;'>{row['Impacto']}</td></tr>"
        delay_content += "</tbody></table></div>"
        st.markdown(
            card("⚠️ Análisis de Retrasos", delay_content), unsafe_allow_html=True
        )

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
