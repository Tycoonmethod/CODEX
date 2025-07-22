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
    # Definir la secuencia de fases para la propagación de delays
    PHASE_SEQUENCE = ["UAT", "Migration", "E2E", "Training", "PRO", "Hypercare"]
    
    try:
        if not penalty_baseline:
            # Para el baseline, sin delays ni reabsorción
            effective_windows = {k: v for k, v in sim_windows.items()}
            
            # Calcular delays y penalizaciones (sin penalizaciones para baseline)
            penalty_factors = {fase: 1.0 for fase in baseline_windows.keys()}

            # Extender el horizonte temporal para la simulación
            start_date = min(effective_windows['UAT'][0], baseline_windows['UAT'][0])
            last_phase_end = max(effective_windows['Hypercare'][1], baseline_windows['Hypercare'][1])
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

                calidad = quality_model_econometric(params, st.session_state.risk_values)
                calidades.append(calidad)

            end_dates = {fase: effective_windows[fase][1] for fase in baseline_windows}
            return fechas_evaluacion, calidades, {}, end_dates

        # --- INICIO DEL NUEVO BLOQUE DE LÓGICA CORREGIDA ---
        else: # Para el escenario, con delays y reabsorción
            try:
                delays = {}
                effective_windows = {k: v for k, v in sim_windows.items()} # Copia inicial

                # 1. Propagación inicial de delays en cadena (sin reabsorción aún)
                for i in range(1, len(PHASE_SEQUENCE)):
                    predecessor = PHASE_SEQUENCE[i-1]
                    current_phase = PHASE_SEQUENCE[i]
                    
                    # La fecha de inicio real es la del slider o el final del predecesor + 1 día
                    actual_start = max(
                        effective_windows[current_phase][0],
                        effective_windows[predecessor][1] + timedelta(days=1)
                    )
                    duration = (effective_windows[current_phase][1] - sim_windows[current_phase][0]).days
                    actual_end = actual_start + timedelta(days=duration)
                    effective_windows[current_phase] = (actual_start, actual_end)

                # 2. Calcular el delay original de Migration (la fuente del problema)
                delay_mig = max(0, (effective_windows["Migration"][1] - baseline_windows["Migration"][1]).days)

                # 3. Leer los factores de reabsorción
                reabsorcion_e2e_pct = st.session_state.get('reabsorcion_e2e', 0) / 100.0
                reabsorcion_training_pct = st.session_state.get('reabsorcion_training', 0) / 100.0

                # 4. Calcular los días reabsorbidos y el retraso neto final
                dias_reabsorbidos = delay_mig * (reabsorcion_e2e_pct + reabsorcion_training_pct)
                net_delay_propagado = max(0, round(delay_mig - dias_reabsorbidos))

                # 5. RECALCULAR las fechas de E2E y Training basándose en el retraso NETO
                mig_end_baseline = baseline_windows["Migration"][1]
                
                e2e_start_corregido = mig_end_baseline + timedelta(days=net_delay_propagado + 1)
                e2e_duration = (sim_windows["E2E"][1] - sim_windows["E2E"][0]).days
                e2e_end_corregido = e2e_start_corregido + timedelta(days=e2e_duration)
                effective_windows["E2E"] = (e2e_start_corregido, e2e_end_corregido)

                train_start_corregido = e2e_end_corregido + timedelta(days=1)
                train_duration = (sim_windows["Training"][1] - sim_windows["Training"][0]).days
                train_end_corregido = train_start_corregido + timedelta(days=train_duration)
                effective_windows["Training"] = (train_start_corregido, train_end_corregido)

                # Calcular delays y penalizaciones basado en las fechas FINALES
                final_delays = {fase: max(0, (effective_windows[fase][1] - baseline_windows[fase][1]).days) for fase in baseline_windows.keys()}
                penalty_factors = {fase: 1 - (delay * DELAY_PENALTY_FACTORS.get(fase, 0)) for fase, delay in final_delays.items()}

                # Extender el horizonte temporal para la simulación
                start_date = min(effective_windows['UAT'][0], baseline_windows['UAT'][0])
                last_phase_end = max(effective_windows['Hypercare'][1], baseline_windows['Hypercare'][1])
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

                    calidad = quality_model_econometric(params, st.session_state.risk_values)
                    calidades.append(calidad)

                end_dates = {fase: effective_windows[fase][1] for fase in baseline_windows}
                return fechas_evaluacion, calidades, final_delays, end_dates

            except Exception as e:
                st.error(f"Error en construir_cronograma_seguro: {type(e).__name__}: {e}")
                st.error(f"Traceback completo: {traceback.format_exc()}")
                return [], [], {}, {}
        # --- FIN DEL NUEVO BLOQUE DE LÓGICA CORREGIDA ---

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
    
    # Initialize risk values for each phase
    if "risk_values" not in st.session_state:
        st.session_state.risk_values = {
            'UAT': 0,
            'Migration': 0,
            'E2E': 0,
            'Training': 0,
            'PRO': 0,
            'Hypercare': 0
        }
    
    # Initialize health score parameters
    if "budget_consumed" not in st.session_state:
        st.session_state.budget_consumed = 100  # Default to 100%
    if "external_risks" not in st.session_state:
        st.session_state.external_risks = 0  # Default to 0%
    
    # Initialize delay reabsorption parameters
    if "reabsorcion_e2e" not in st.session_state:
        st.session_state.reabsorcion_e2e = 0  # Default to 0%
    if "reabsorcion_training" not in st.session_state:
        st.session_state.reabsorcion_training = 0  # Default to 0%
    
    # Initialize scenario management
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = {}
    if "compare_scenarios" not in st.session_state:
        st.session_state.compare_scenarios = []
    if "scenario_name" not in st.session_state:
        st.session_state.scenario_name = ""
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
    
    # Risk Inputs Section
    st.markdown("---")
    with st.expander("⚠️ Riesgos de Ejecución por Fase", expanded=False):
        st.markdown("#### Ajusta el nivel de riesgo para cada fase del proyecto")
        
        # Create sliders for each phase's risk
        for phase in ['UAT', 'Migration', 'E2E', 'Training', 'PRO', 'Hypercare']:
            st.session_state.risk_values[phase] = st.slider(
                f"Riesgo {phase} (%)",
                0, 100, 
                value=st.session_state.risk_values[phase],
                key=f"risk_slider_{phase}",
                help=f"Riesgo específico para la fase {phase}. Un riesgo alto degradará la calidad de esta fase y afectará las fases posteriores."
            )
    
    # Delay Reabsorption Section
    with st.expander("🔄 Factores de Reabsorción de Retrasos", expanded=False):
        st.markdown("#### Configura la capacidad de reabsorción de delays por fase")
        
        st.slider(
            "Reabsorción de Delay en E2E (%)",
            0, 100,
            value=st.session_state.reabsorcion_e2e,
            key="reabsorcion_e2e",
            help="Porcentaje del retraso acumulado que el equipo de E2E puede reabsorber."
        )
        
        st.slider(
            "Reabsorción de Delay en Training (%)",
            0, 100,
            value=st.session_state.reabsorcion_training,
            key="reabsorcion_training",
            help="Porcentaje del retraso acumulado que el equipo de Training puede reabsorber."
        )
    
    # Health Score Parameters Section
    with st.expander("🏥 Parámetros de Salud del Proyecto", expanded=False):
        st.markdown("#### Configura los factores que afectan la salud general del proyecto")
        
        st.session_state.budget_consumed = st.slider(
            "💰 % Presupuesto Consumido",
            0, 200,
            value=st.session_state.budget_consumed,
            key="budget_consumed_slider",
            help="Porcentaje del presupuesto que se ha consumido. Más de 100% indica sobrecostos."
        )
        
        st.session_state.external_risks = st.slider(
            "⚠️ Riesgos Externos Agregados",
            0, 100,
            value=st.session_state.external_risks,
            key="external_risks_slider",
            help="Riesgos externos adicionales que afectan la salud del proyecto (cambios de alcance, problemas técnicos, etc.)."
        )
    
    # Scenario Management Section
    st.markdown("---")
    with st.expander("📁 Gestión de Escenarios", expanded=False):
        st.markdown("#### Guarda y compara diferentes configuraciones del proyecto")
        
        # Scenario name input
        scenario_name = st.text_input("Nombre del Escenario", key="scenario_name_input")
        
        # Save current scenario
        if st.button("💾 Guardar Escenario Actual", use_container_width=True):
            if not scenario_name:
                st.error("Por favor, ingrese un nombre para el escenario")
            else:
                # Collect current scenario parameters
                current_scenario = {
                    'sliders': scenario_windows.copy(),
                    'risks': st.session_state.risk_values.copy(),
                    'budget_consumed': st.session_state.budget_consumed,
                    'external_risks': st.session_state.external_risks,
                    'reabsorcion_e2e': st.session_state.reabsorcion_e2e,
                    'reabsorcion_training': st.session_state.reabsorcion_training,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.scenarios[scenario_name] = current_scenario
                st.success(f"✅ Escenario '{scenario_name}' guardado")
        
        # Scenario comparison selector
        if st.session_state.scenarios:
            st.markdown("##### 📊 Comparar Escenarios")
            st.session_state.compare_scenarios = st.multiselect(
                "Seleccionar escenarios a comparar",
                options=list(st.session_state.scenarios.keys()),
                default=st.session_state.compare_scenarios,
                help="Selecciona múltiples escenarios para compararlos en el gráfico"
            )
            
            # Show saved scenarios
            st.markdown("##### 💾 Escenarios Disponibles")
            for name, data in st.session_state.scenarios.items():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**{name}**")
                    st.caption(f"Guardado: {data['timestamp']}")
                
                with col2:
                    if st.button("📥 Cargar", key=f"load_{name}"):
                        # Update scenario windows with saved values
                        scenario_windows = data['sliders'].copy()
                        st.session_state.risk_values = data['risks'].copy()
                        st.session_state.budget_consumed = data['budget_consumed']
                        st.session_state.external_risks = data['external_risks']
                        # Load reabsorption parameters if they exist in the saved scenario
                        if 'reabsorcion_e2e' in data:
                            st.session_state.reabsorcion_e2e = data['reabsorcion_e2e']
                        if 'reabsorcion_training' in data:
                            st.session_state.reabsorcion_training = data['reabsorcion_training']
                        st.success(f"✅ Escenario '{name}' cargado")
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Eliminar", key=f"delete_{name}"):
                        del st.session_state.scenarios[name]
                        if name in st.session_state.compare_scenarios:
                            st.session_state.compare_scenarios.remove(name)
                        st.success(f"✅ Escenario '{name}' eliminado")
                        st.rerun()
                
                st.markdown("---")

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

# --- KPIs Panel ---
st.markdown("### 📊 KPIs del Proyecto")

# Calculate additional KPIs
try:
    # 1. Retraso Total del Proyecto
    project_end = max(fechas_esc)
    baseline_end = max(fechas_base)
    total_delay = (project_end - baseline_end).days
    
    # 2. Salud General del Proyecto
    from phase_model import calculate_health_score
    from constants import HEALTH_THRESHOLDS
    current_quality = calidad_esc[-1] if calidad_esc else 0
    baseline_quality_final = calidad_base[-1] if calidad_base else 0
    
    # Calculate health score with new parameters
    health_score = calculate_health_score(
        quality=current_quality,
        delay_days=total_delay,
        budget_pct_used=st.session_state.budget_consumed,
        sum_risks=st.session_state.external_risks
    )
    
    baseline_health_score = calculate_health_score(
        quality=baseline_quality_final,
        delay_days=0,
        budget_pct_used=100,
        sum_risks=0
    )
    
    health_delta = health_score - baseline_health_score
    
    # --- INICIO DEL BLOQUE DE CORRECCIÓN VISUAL ---
    # Encontrar la primera fecha donde hay un cambio real
    primera_fecha_impacto = None
    for fase in ["UAT", "Migration", "E2E", "Training", "PRO", "Hypercare"]:
        if scenario_windows[fase][0] != baseline_windows[fase][0] or scenario_windows[fase][1] != baseline_windows[fase][1]:
            primera_fecha_impacto = min(scenario_windows[fase][0], baseline_windows[fase][0])
            break

    # Si hay un punto de impacto, forzar que la curva del escenario sea igual a la del baseline hasta ese punto.
    if primera_fecha_impacto:
        df_baseline_interp = pd.DataFrame(index=fechas_esc, data={'baseline_quality': np.interp(fechas_esc.astype(np.int64), fechas_base.astype(np.int64), calidad_base)})
        calidad_esc = np.where(fechas_esc < primera_fecha_impacto, df_baseline_interp['baseline_quality'], calidad_esc)
    # --- FIN DEL BLOQUE DE CORRECCIÓN VISUAL ---
    
    # Display KPIs in 3 columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🎯 Calidad Go-Live",
            f"{calidad_esc_gl:.1f}%",
            delta=f"{delta_gl:.1f}%",
            help="Calidad del proyecto en la fecha de Go-Live (3-Nov-2025)"
        )
    
    with col2:
        st.metric(
            "⏰ Retraso Total",
            f"{total_delay} días",
            delta=f"{total_delay} días",
            delta_color="inverse",
            help="Diferencia en días entre la fecha final del escenario y el baseline"
        )
    
    with col3:
        # Add title for health score (same style as other KPIs)
        st.markdown("**🏥 Health Score**")
        
        # Create gauge chart for health score
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "", 'font': {'size': 12}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "darkblue"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, HEALTH_THRESHOLDS['critical']], 'color': "red"},
                    {'range': [HEALTH_THRESHOLDS['critical'], HEALTH_THRESHOLDS['warning']], 'color': "yellow"},
                    {'range': [HEALTH_THRESHOLDS['warning'], 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 3},
                    'thickness': 0.75,
                    'value': HEALTH_THRESHOLDS['critical']
                }
            }
        ))
        
        fig_gauge.update_layout(
            height=150,
            margin=dict(t=20, b=20, l=20, r=20),
            font={'size': 10},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False}, height=150)
    
except Exception as e:
    st.error(f"Error calculando KPIs: {str(e)}")

st.markdown("---")

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
    
    # Add comparison scenarios
    if st.session_state.compare_scenarios:
        # Define colors for comparison scenarios
        comparison_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        
        for i, scenario_name in enumerate(st.session_state.compare_scenarios):
            if scenario_name in st.session_state.scenarios:
                scenario_data = st.session_state.scenarios[scenario_name]
                
                # Calculate timeline for this scenario
                try:
                    comp_fechas, comp_calidad, _, _ = construir_cronograma_seguro(
                        sim_windows=scenario_data['sliders'],
                        penalty_baseline=baseline_windows
                    )
                    
                    # Add comparison trace
                    color = comparison_colors[i % len(comparison_colors)]
                    fig.add_trace(
                        go.Scatter(
                            x=[d.strftime("%Y-%m-%d") for d in comp_fechas],
                            y=comp_calidad,
                            name=f"Escenario: {scenario_name}",
                            line=dict(color=color, width=2, dash='dot'),
                            hovertemplate=f"%{{y:.1f}}%<extra>{scenario_name}</extra>",
                        )
                    )
                except Exception as e:
                    st.warning(f"Error calculando escenario '{scenario_name}': {str(e)}")

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
                st.rerun()  # <--- AÑADE ESTA LÍNEA
                st.success(f"💡 **Fecha sugerida: {new_golive_date.strftime('%d-%b-%Y')}** (visualizada en el gráfico)")
            else:
                max_quality = quality_array[-1]
                # Si no se encuentra, limpiar la fecha sugerida anterior
                if 'suggested_golive_date' in st.session_state:
                    del st.session_state.suggested_golive_date
                st.error(f"❌ Imposible alcanzar. La calidad máxima del nuevo plan sería de **{max_quality:.1f}%**.")
        else:
            st.error("Error: No se pudo simular el nuevo plan.")
