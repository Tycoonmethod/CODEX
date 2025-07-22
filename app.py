import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, date, time as dt_time, timedelta
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
st.set_page_config(page_title="Modelo Go-Live", layout="wide")

# Inject custom CSS
inject_custom_css()

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

def quality_model_econometric(params, risk_params=None):
    """
    Modelo econométrico mejorado donde Migration es verdaderamente crítica
    Incluye factores de riesgo por fase
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

    # Aplicar factores de riesgo si están disponibles
    if risk_params:
        # Risk impact factors for each phase (higher = more sensitive to risk)
        risk_impact_factors = {
            'Migration': 0.40,  # Most sensitive
            'PRO': 0.35,       # Second most sensitive
            'UAT': 0.25,       # Medium-high sensitivity
            'E2E': 0.20,       # Medium sensitivity
            'Training': 0.20,  # Medium sensitivity
            'Hypercare': 0.15  # Least sensitive
        }
        
        # Apply risk impact to each phase
        for phase in ['UAT', 'Migration', 'E2E', 'Training', 'PRO', 'Hypercare']:
            if phase in risk_params and risk_params[phase] > 0:
                risk_factor = risk_params[phase] / 100
                risk_impact = risk_factor * risk_factor  # Quadratic scaling
                phase_risk_factor = risk_impact_factors.get(phase, 0.20)
                
                # Reduce the phase completion based on risk
                if phase == 'UAT':
                    uat_pct *= (1 - risk_impact * phase_risk_factor)
                elif phase == 'Migration':
                    migration_pct *= (1 - risk_impact * phase_risk_factor)
                elif phase == 'E2E':
                    e2e_pct *= (1 - risk_impact * phase_risk_factor)
                elif phase == 'Training':
                    training_pct *= (1 - risk_impact * phase_risk_factor)
                elif phase == 'PRO':
                    pro_pct *= (1 - risk_impact * phase_risk_factor)
                elif phase == 'Hypercare':
                    hypercare_pct *= (1 - risk_impact * phase_risk_factor)

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

    return max(0, min(100, valor_original * 100))


def get_completion_pct(
    start: datetime, end: datetime, eval_date: datetime, baseline_duration: int = None
) -> float:
    """
    Calcula el porcentaje de completitud de una fase en una fecha específica.
    Maneja fechas como strings, datetime, o date.
    """
    # Convertir fechas si son strings
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d")
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d")
    if isinstance(eval_date, str):
        eval_date = datetime.strptime(eval_date, "%Y-%m-%d")
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, dt_time.min)
    if isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, dt_time.min)
    if isinstance(eval_date, date) and not isinstance(eval_date, datetime):
        eval_date = datetime.combine(eval_date, dt_time.min)

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
        return datetime.now()
    if isinstance(x, datetime):
        return x
    if isinstance(x, date):
        return datetime.combine(x, dt_time.min)
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
        start_date = datetime.combine(start_date, dt_time.min)
    if isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, dt_time.min)
    return (end_date - start_date).days


def add_days(base_date, days):
    """Añade días a una fecha, manejando None"""
    if base_date is None:
        return datetime.now()
    if isinstance(base_date, str):
        base_date = datetime.strptime(base_date, "%Y-%m-%d")
    if isinstance(base_date, date) and not isinstance(base_date, datetime):
        base_date = datetime.combine(base_date, dt_time.min)
    return base_date + timedelta(days=days)


# --- Baseline Windows ---
baseline_windows = {
    "UAT": (datetime(2025, 7, 8), datetime(2025, 7, 31)),
    "Migration": (datetime(2025, 8, 1), datetime(2025, 8, 31)),
    "E2E": (datetime(2025, 9, 1), datetime(2025, 9, 30)),
    "Training": (datetime(2025, 10, 1), datetime(2025, 10, 31)),
    "PRO": (datetime(2025, 10, 1), datetime(2025, 10, 30)),
    "Hypercare": (datetime(2025, 11, 3), datetime(2025, 12, 3)),
}

baseline_days = {
    "UAT": 23,
    "Migration": 31,
    "E2E": 30,
    "Training": 31,
    "PRO": 30,
    "Hypercare": 30,
}

# --- Inicialización de variables de sesión ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.lang = 'es'
    st.session_state.risk_values = {phase: 0 for phase in baseline_windows.keys()}
    st.session_state.external_risks = 0
    st.session_state.budget_consumed = 75

# --- Language Selector ---
language = st.sidebar.selectbox(
    "Idioma / Language",
    options=list(LANGUAGES.keys()),
    format_func=lambda x: LANGUAGES[x],
    index=list(LANGUAGES.keys()).index(st.session_state.lang),
    key='language_selector'
)

# Actualizar idioma si cambió
if language != st.session_state.lang:
    st.session_state.lang = language
    st.rerun()

# --- Título y descripción ---
st.title("📊 Modelo Interactivo")
st.markdown("Simula y analiza el proceso de Go-Live con un modelo econométrico avanzado")

# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    # Risk sliders
    st.subheader("⚠️ Riesgos por Fase")
    for phase in baseline_windows.keys():
        st.session_state.risk_values[phase] = st.slider(
            f"Riesgo {phase} (%)",
            0, 100, st.session_state.risk_values.get(phase, 0),
            help=f"Riesgo asociado a la fase {phase}"
        )
    
    # External risks
    st.subheader("🌍 Riesgos Externos")
    st.session_state.external_risks = st.slider(
        "Riesgo Externo Total (%)",
        0, 100, st.session_state.external_risks,
        help="Riesgos externos que afectan todo el proyecto"
    )
    
    # Budget
    st.subheader("💰 Presupuesto")
    st.session_state.budget_consumed = st.slider(
        "Presupuesto Consumido (%)",
        0, 100, st.session_state.budget_consumed,
        help="Porcentaje del presupuesto ya consumido"
    )

# --- Main Content ---
st.markdown("### 🎯 Análisis de Calidad del Proyecto")

# Calculate countdown to Go-Live
dias_para_golive = max(
    0, (to_dt(datetime(2025, 11, 3)) - to_dt(datetime.now().date())).days
)

# Display countdown
st.metric(
    "⏰ Días hasta Go-Live",
    f"{dias_para_golive} días",
    help="Días restantes hasta la fecha de Go-Live (3-Nov-2025)"
)

# --- Quality Analysis ---
st.markdown("### 📈 Análisis de Calidad")

# Calculate quality for current scenario
current_params = {}
for phase in baseline_windows.keys():
    current_params[phase] = 0.8  # Default 80% completion

current_quality = quality_model_econometric(current_params, st.session_state.risk_values)

# Display quality metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "🎯 Calidad Actual",
        f"{current_quality:.1f}%",
        help="Calidad del proyecto con la configuración actual"
    )

with col2:
    st.metric(
        "⚠️ Riesgo Total",
        f"{sum(st.session_state.risk_values.values())}%",
        help="Suma de todos los riesgos por fase"
    )

with col3:
    st.metric(
        "💰 Presupuesto",
        f"{st.session_state.budget_consumed}%",
        help="Porcentaje del presupuesto consumido"
    )

# --- Recommendations ---
st.markdown("### 💡 Recomendaciones")

if current_quality < 80:
    st.warning("⚠️ La calidad del proyecto está por debajo del objetivo. Considera:")
    st.markdown("- Revisar los riesgos en las fases críticas")
    st.markdown("- Optimizar la planificación de Migration")
    st.markdown("- Evaluar recursos adicionales")
elif current_quality >= 80:
    st.success("✅ La calidad del proyecto está en buen nivel")
    st.markdown("- Mantén el control de riesgos")
    st.markdown("- Continúa monitoreando las fases críticas")

# --- Footer ---
st.markdown("---")
st.markdown("*Modelo desarrollado para análisis de proyectos Go-Live*")
