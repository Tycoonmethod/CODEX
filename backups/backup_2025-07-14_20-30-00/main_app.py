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
import pulp

# --- UI Configuration ---
st.set_page_config(page_title="Modelo Go-Live", layout="wide")

# Inject custom CSS
inject_custom_css()

# --- State Initialization ---
def initialize_state():
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "home"
    if "lang" not in st.session_state:
        st.session_state.lang = "es"
    if "saved_scenarios" not in st.session_state:
        st.session_state.saved_scenarios = {}
    if "compare_scenarios" not in st.session_state:
        st.session_state.compare_scenarios = set()
    # Add other state variables from ultra_current.py as needed

initialize_state()

# --- Language Selector ---
_, col2 = st.columns([0.85, 0.15])
with col2:
    selected_lang_display = st.selectbox(
        " ", list(LANGUAGES.keys()), label_visibility="collapsed"
    )
    st.session_state.lang = LANGUAGES[selected_lang_display]

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("### 📊 Navegación")

    # Page selector
    page_options = {
        "🏠 Inicio": "home",
        "📊 Modelo Interactivo": "modelo",
        "💰 Análisis Financiero": "financiero"
    }

    selected_page_display = st.selectbox(
        "Seleccionar página:",
        list(page_options.keys()),
        index=list(page_options.values()).index(st.session_state.selected_page),
    )
    st.session_state.selected_page = page_options[selected_page_display]

    st.markdown("---")

# Import all the helper functions from ultra_current.py
def quality_model_econometric(params, sum_risks=0):
    """
    Modelo econométrico mejorado donde Migration es verdaderamente crítica
    Incluye penalización por riesgos externos
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

    # Aplicar penalización por riesgo
    risk_penalty_factor = sum_risks * 0.0005  # Un 0.05% de penalización por cada punto de riesgo
    calidad_penalizada = calidad_normalizada * (1 - risk_penalty_factor)

    return min(max(calidad_penalizada, 0), 100)

def monte_carlo_quality_model(params, iterations=1000, sum_risks=0):
    """
    Enhanced Monte Carlo simulation for quality prediction with conditional deterministic mode
    """
    # If no risks, return deterministic result (no bands)
    if sum_risks == 0:
        base_quality = quality_model_econometric(params, sum_risks=0)
        return [base_quality], 0.0

    qualities = []

    # Proportional noise based on total risks: higher risks = more uncertainty
    noise_std = 0.02 * (sum_risks / 300)  # Scale noise with risk level

    for _ in range(iterations):
        # Create noisy parameters
        noisy_params = {}
        for key, value in params.items():
            if key == "Resources":
                # Resources have different noise characteristics
                noise = np.random.normal(0, noise_std)
            else:
                # Phase completion noise
                noise = np.random.normal(0, noise_std)

            noisy_value = value + noise
            noisy_params[key] = max(0, min(1, noisy_value))  # Clamp to [0,1]

        # Calculate quality with noisy parameters and risk penalty
        quality = quality_model_econometric(noisy_params, sum_risks=sum_risks)
        qualities.append(quality)

    mean_quality = np.mean(qualities)
    std_quality = np.std(qualities)

    return qualities, std_quality

def get_completion_pct(
    start: datetime, end: datetime, eval_date: datetime, baseline_duration: int = 0
) -> float:
    """
    Devuelve el % completitud de una fase:
      - Si eval_date < start: 0%
      - Si start <= eval_date < end: progresión lineal
      - Si eval_date >= end:
          * Si baseline_duration 0: 100%
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
        if baseline_duration > 0 and actual > baseline_duration:
            pct = (baseline_duration / actual) * 100
        else:
            pct = 100.0

    # Aplica siempre el techo en el tramo de ejecución
    if baseline_duration > 0 and actual > baseline_duration:
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

def construir_cronograma_seguro(scenario_windows, es_baseline=False, sum_risks=0):
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
            calidades_std = []
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

                # Use Monte Carlo with conditional bands based on risks
                params = {
                    "UAT": uat_pct / 100,
                    "Migration": mig_pct / 100,
                    "E2E": e2e_pct / 100,
                    "Training": train_pct / 100,
                    "PRO": pro_pct / 100,
                    "Resources": 0,
                    "Hypercare": hyper_pct / 100,
                }

                # For baseline, force sum_risks = 0 (no bands)
                current_sum_risks = 0 if es_baseline else sum_risks
                qualities_mc, std_mc = monte_carlo_quality_model(
                    params, iterations=100, sum_risks=current_sum_risks
                )
                calidad = np.mean(qualities_mc)
                calidades.append(calidad)
                calidades_std.append(std_mc)

            # Recopilar fechas finales baseline
            end_dates = {fase: baseline_windows[fase][1] for fase in baseline_windows}

            return fechas_evaluacion, calidades, calidades_std, {}, end_dates

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
            calidades_std = []
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

                # Use Monte Carlo with conditional bands based on risks
                params = {
                    "UAT": uat_pct / 100,
                    "Migration": mig_pct / 100,
                    "E2E": e2e_pct / 100,
                    "Training": train_pct / 100,  # <— ahora dinámico del slider
                    "PRO": pro_pct / 100,  # <— ahora dinámico del slider
                    "Resources": 0,
                    "Hypercare": hyper_pct / 100,
                }

                qualities_mc, std_mc = monte_carlo_quality_model(
                    params, iterations=100, sum_risks=sum_risks
                )
                calidad = np.mean(qualities_mc)
                calidades.append(calidad)
                calidades_std.append(std_mc)

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
            return fechas_evaluacion, calidades, calidades_std, delays, end_dates

    except Exception as e:
        st.error(f"Error en construir_cronograma_seguro: {type(e).__name__}: {e}")
        st.error(f"Traceback completo: {traceback.format_exc()}")
        return None, None, None, None, None

def optimizar_delays(target_quality):
    """
    Optimiza los días de cada fase para alcanzar una calidad objetivo minimizando delays
    
    Args:
        target_quality: Calidad objetivo a alcanzar (0-100)
        
    Returns:
        dict: Diccionario con los días óptimos para cada fase o None si no hay solución
    """
    try:
        # Crear el problema de optimización
        prob = pulp.LpProblem("Optimizar_GoLive", pulp.LpMinimize)

        # Definir variables (días para cada fase)
        # Los límites vienen de los sliders en la UI
        uat_days = pulp.LpVariable("uat_days", 15, 45)
        migration_days = pulp.LpVariable("migration_days", 20, 60)
        e2e_days = pulp.LpVariable("e2e_days", 20, 50)
        training_days = pulp.LpVariable("training_days", 20, 50)

        # Calcular delays respecto al baseline
        delay_uat = uat_days - baseline_days["UAT"]
        delay_migration = migration_days - baseline_days["Migration"]
        delay_e2e = e2e_days - baseline_days["E2E"]
        delay_training = training_days - baseline_days["Training"]

        # Función objetivo: minimizar el delay total, con peso extra en Migration
        prob += 2 * delay_migration + delay_uat + delay_e2e + delay_training

        # Restricciones de calidad usando el modelo econométrico
        # Convertir días a porcentajes para el modelo
        uat_pct = uat_days / baseline_days["UAT"]
        migration_pct = migration_days / baseline_days["Migration"]
        e2e_pct = e2e_days / baseline_days["E2E"]
        training_pct = training_days / baseline_days["Training"]

        # Restricción de calidad mínima
        # Usamos una aproximación lineal del modelo econométrico para PuLP
        prob += (
            (1.00  # Intercepto
            + 0.25 * uat_pct  # UAT
            + 0.40 * migration_pct  # Migration (crítica)
            + 0.20 * e2e_pct  # E2E
            + 0.15 * training_pct  # Training
            + 0.10 * 1.0  # Resources (asumimos 100%)
            + 0.10 * 1.0)  # Hypercare (asumimos 100%)
            / 2.20  # Factor normalización
            * 100  # Convertir a porcentaje
            >= target_quality
        )

        # Restricciones de dependencia
        # Migration depende de UAT
        prob += migration_days >= uat_days + 1
        # E2E depende de Migration
        prob += e2e_days >= migration_days + 1
        # Training depende de E2E
        prob += training_days >= e2e_days + 1

        # Resolver el problema
        status = prob.solve()

        # Si encontró solución
        if status == pulp.LpStatusOptimal:
            return {
                "UAT": int(str(pulp.value(uat_days)).split('.')[0]),
                "Migration": int(str(pulp.value(migration_days)).split('.')[0]),
                "E2E": int(str(pulp.value(e2e_days)).split('.')[0]),
                "Training": int(str(pulp.value(training_days)).split('.')[0])
            }
        else:
            return None

    except Exception as e:
        st.error(f"Error en optimización: {str(e)}")
        return None

# --- Page Content ---
if st.session_state.selected_page == "home":
    # Home Page Content
    st.title("🏠 Bienvenido al Modelo Go-Live")
    st.markdown("""
    Esta aplicación te permite:
    
    - 📊 **Modelo Interactivo**: Simular y analizar el proceso de Go-Live con un modelo econométrico avanzado
    - 💰 **Análisis Financiero**: Evaluar el impacto financiero y ROI del proyecto
    - 📈 **Visualizaciones**: Ver gráficos detallados y métricas clave
    """)

elif st.session_state.selected_page == "modelo":
    # Modelo Interactivo Content (from ultra_current.py)
    st.title("📊 Modelo Interactivo")
    
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

        # External Risk Factors
        st.subheader("⚠️ Factores de Riesgo Externos")
        if "external_risks" not in st.session_state:
            st.session_state.external_risks = {
                "tech_risk": 0,
                "business_risk": 0,
                "scope_changes": 0,
            }

        st.session_state.external_risks["tech_risk"] = st.slider(
            "Riesgo Técnico (%)",
            0,
            100,
            st.session_state.external_risks["tech_risk"],
            help="0% = Sin riesgo técnico (óptimo para baseline ~95.5%)",
        )
        st.session_state.external_risks["business_risk"] = st.slider(
            "Riesgo de Negocio (%)",
            0,
            100,
            st.session_state.external_risks["business_risk"],
            help="0% = Sin riesgo de negocio (óptimo para baseline ~95.5%)",
        )
        st.session_state.external_risks["scope_changes"] = st.slider(
            "Cambios de Alcance (%)",
            0,
            100,
            st.session_state.external_risks["scope_changes"],
            help="0% = Sin cambios de alcance (óptimo para baseline ~95.5%)",
        )

        # Note about uncertainty bands
        st.info("💡 **Riesgos >0 activan bandas de incertidumbre** (Monte Carlo varianza)")

        # Optimization section
        with st.expander("🤖 Optimización Automática", expanded=False):
            target_quality = st.number_input(
                "Calidad Objetivo (%)",
                min_value=70,
                max_value=95,
                value=90,
                help="Define la calidad mínima que deseas alcanzar",
            )
            
            if st.button("Encontrar Fechas Óptimas", use_container_width=True):
                # Call optimization function
                optimal_days = optimizar_delays(target_quality)
                
                if optimal_days:
                    # Update sliders with optimal values
                    for fase, dias in optimal_days.items():
                        # Calculate new start and end dates
                        start_date = baseline_windows[fase][0]
                        end_date = start_date + timedelta(days=int(dias))
                        
                        # Update session state for the slider
                        st.session_state[f"slider_{fase}"] = (start_date, end_date)
                    
                    st.success(f"✅ Solución encontrada para calidad objetivo {target_quality}%")
                    st.rerun()  # Refresh to update sliders
                else:
                    st.error(
                        """❌ No es posible alcanzar la calidad objetivo. 
                        Intenta reducirla o mitigar riesgos."""
                    )

        # Scenario Management Section
        st.subheader("📁 Gestión de Escenarios")
        
        # Input for scenario name
        scenario_name = st.text_input("Nombre del Escenario", key="scenario_name")
        
        # Save button
        if st.button("💾 Guardar Escenario Actual", use_container_width=True):
            if not scenario_name:
                st.error("Por favor, ingresa un nombre para el escenario")
            else:
                # Save current state
                current_scenario = {
                    "sliders": {
                        fase: st.session_state[f"slider_{fase}"]
                        for fase in baseline_windows.keys()
                    },
                    "risks": dict(st.session_state.external_risks),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.saved_scenarios[scenario_name] = current_scenario
                st.success(f"✅ Escenario '{scenario_name}' guardado exitosamente")
        
        # Display saved scenarios
        if st.session_state.saved_scenarios:
            st.markdown("#### Escenarios Guardados")
            
            for name, scenario in st.session_state.saved_scenarios.items():
                with st.expander(f"📊 {name} ({scenario['timestamp']})"):
                    col1, col2 = st.columns([0.7, 0.3])
                    
                    with col1:
                        # Checkbox for comparison
                        compare = st.checkbox(
                            "Comparar",
                            value=name in st.session_state.compare_scenarios,
                            key=f"compare_{name}"
                        )
                        if compare:
                            st.session_state.compare_scenarios.add(name)
                        else:
                            st.session_state.compare_scenarios.discard(name)
                    
                    with col2:
                        # Load button
                        if st.button("📥 Cargar", key=f"load_{name}"):
                            # Restore sliders
                            for fase, value in scenario["sliders"].items():
                                st.session_state[f"slider_{fase}"] = value
                            # Restore risks
                            st.session_state.external_risks = dict(scenario["risks"])
                            st.success(f"✅ Escenario '{name}' cargado")
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

    # Calculate sum of risks for conditional bands
    sum_risks = (
        st.session_state.external_risks["tech_risk"]
        + st.session_state.external_risks["business_risk"]
        + st.session_state.external_risks["scope_changes"]
    )

    # Construir cronograma baseline (always deterministic, no bands)
    fechas_base, calidad_base_mean, calidad_base_std, delays_base, end_dates_base = (
        construir_cronograma_seguro(baseline_windows, es_baseline=True, sum_risks=0)
    )

    # Construir cronograma escenario (conditional bands based on risks)
    fechas_esc, calidad_esc_mean, calidad_esc_std, delays_esc, end_dates_esc = (
        construir_cronograma_seguro(
            scenario_windows, es_baseline=False, sum_risks=sum_risks
        )
    )

    # --- PUNTO: interpolar calidad en Go-Live ---
    go_live_date = datetime(2025, 11, 3)

    # Convertir a timestamps
    base_ts = [f.timestamp() for f in fechas_base]
    esc_ts = [f.timestamp() for f in fechas_esc]

    # Interpolación
    calidad_base_gl = np.interp(go_live_date.timestamp(), base_ts, calidad_base_mean)
    calidad_esc_gl = np.interp(go_live_date.timestamp(), esc_ts, calidad_esc_mean)
    calidad_base_std_gl = np.interp(go_live_date.timestamp(), base_ts, calidad_base_std)
    calidad_esc_std_gl = np.interp(go_live_date.timestamp(), esc_ts, calidad_esc_std)
    delta_gl = calidad_esc_gl - calidad_base_gl

    # Countdown hasta Go-Live
    dias_para_golive = max(
        0, (to_dt(datetime(2025, 11, 3)) - to_dt(datetime.now().date())).days
    )

    # Main content area with cards
    with main_container:
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

        # Add baseline trace (no bands, always deterministic)
        fig.add_trace(
            go.Scatter(
                x=[d.strftime("%Y-%m-%d") for d in fechas_base],
                y=calidad_base_mean,
                name="Baseline",
                line=dict(color=COLORS["baseline"], width=2),
                hovertemplate="%{y:.1f}%<extra>Baseline</extra>",
            )
        )

        # Add scenario confidence bands only if risks > 0
        if np.mean(calidad_esc_std) > 0:
            # Upper band
            fig.add_trace(
                go.Scatter(
                    x=[d.strftime("%Y-%m-%d") for d in fechas_esc],
                    y=np.array(calidad_esc_mean) + np.array(calidad_esc_std),
                    mode="lines",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                    name="scenario_upper",
                )
            )

            # Lower band
            fig.add_trace(
                go.Scatter(
                    x=[d.strftime("%Y-%m-%d") for d in fechas_esc],
                    y=np.array(calidad_esc_mean) - np.array(calidad_esc_std),
                    mode="lines",
                    line=dict(width=0),
                    fillcolor=COLORS["band"],
                    fill="tonexty",
                    showlegend=False,
                    hoverinfo="skip",
                    name="scenario_lower",
                )
            )

        # Add scenario mean line
        fig.add_trace(
            go.Scatter(
                x=[d.strftime("%Y-%m-%d") for d in fechas_esc],
                y=calidad_esc_mean,
                name="Escenario Actual",
                line=dict(color=COLORS["scenario"], width=2),
                hovertemplate="%{y:.1f}%<extra>Escenario Actual</extra>",
            )
        )

        # Add comparison scenarios if any are selected
        comparison_colors = [COLORS["success"], COLORS["warning"], COLORS["danger"]]
        for i, scenario_name in enumerate(st.session_state.compare_scenarios):
            if scenario_name in st.session_state.saved_scenarios:
                scenario = st.session_state.saved_scenarios[scenario_name]
                
                # Build scenario windows from saved data
                comp_scenario_windows = {}
                for fase, value in scenario["sliders"].items():
                    comp_scenario_windows[fase] = value
                
                # Calculate quality curve for comparison scenario
                comp_fechas, comp_calidad_mean, comp_calidad_std, _, _ = construir_cronograma_seguro(
                    comp_scenario_windows,
                    es_baseline=False,
                    sum_risks=sum(scenario["risks"].values())
                )
                
                # Add comparison scenario trace
                color = comparison_colors[i % len(comparison_colors)]
                fig.add_trace(
                    go.Scatter(
                        x=[d.strftime("%Y-%m-%d") for d in comp_fechas],
                        y=comp_calidad_mean,
                        name=f"Escenario: {scenario_name}",
                        line=dict(color=color, width=2, dash="dot"),
                        hovertemplate=f"%{{y:.1f}}%<extra>{scenario_name}</extra>",
                    )
                )

        # Add Go-Live vertical line
        fig.add_shape(
            type="line",
            x0=go_live_date.strftime("%Y-%m-%d"),
            x1=go_live_date.strftime("%Y-%m-%d"),
            y0=0,
            y1=100,
            line=dict(
                color=COLORS["golive"],
                width=2,
                dash="dash",
            ),
        )
        
        # Add Go-Live annotation
        fig.add_annotation(
            x=go_live_date.strftime("%Y-%m-%d"),
            y=100,
            text="Go-Live",
            showarrow=False,
            yshift=10,
        )

        # Update layout
        fig.update_layout(
            showlegend=True,
            hovermode="x unified",
            title={
                "text": "Evolución de Calidad",
                "x": 0.5,
                "xanchor": "center",
                "font": dict(color=COLORS["text"])
            },
            xaxis_title="Fecha",
            yaxis_title="Calidad (%)",
            yaxis=dict(range=[0, 100]),
            paper_bgcolor=PLOT_LAYOUT["paper_bgcolor"],
            plot_bgcolor=PLOT_LAYOUT["plot_bgcolor"],
            font=PLOT_LAYOUT["font"],
            margin=PLOT_LAYOUT["margin"],
            template=PLOT_LAYOUT["template"],
            xaxis=dict(
                gridcolor="rgba(255,255,255,0.1)",
                zerolinecolor="rgba(255,255,255,0.2)",
            ),
            yaxis_gridcolor="rgba(255,255,255,0.1)",
            yaxis_zerolinecolor="rgba(255,255,255,0.2)",
            legend=dict(
                bgcolor="rgba(49,51,63,0.7)",
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1
            )
        )

        # Show the plot
        st.plotly_chart(fig, use_container_width=True)

        # Add risk penalty information
        st.info(
            """💡 **Impacto del Riesgo en la Calidad**
            
            La calidad media del escenario ahora incluye una penalización basada en los factores de riesgo externos. A mayor riesgo, menor calidad esperada.
            
            - Riesgo Total Actual: {}%
            - Penalización Aplicada: {:.1f}%
            """.format(
                sum_risks,
                sum_risks * 0.05  # 0.05% por punto de riesgo
            )
        )

        # Alertas automáticas
        st.subheader("🚨 Alertas Automáticas")

        alertas = []
        if delays_esc and delays_esc.get("Migration", 0) > 0:
            alertas.append(f"🔴 CRÍTICO: Migration con {delays_esc['Migration']} días de delay")
        if sum_risks > 150:
            alertas.append("🔴 CRÍTICO: Riesgo del proyecto muy alto")
        if calidad_esc_gl < 80:
            alertas.append("🔴 CRÍTICO: Calidad por debajo del umbral")

        if alertas:
            for alerta in alertas:
                st.error(alerta)
        else:
            st.success("✅ Todos los indicadores en rango normal")

elif st.session_state.selected_page == "financiero":
    # Financial Analysis Content
    st.title("💰 Análisis Financiero")
    
    # Sidebar configuration for financial parameters
    with st.sidebar:
        st.subheader("📊 Parámetros Financieros")
        with st.expander("💰 Configuración Financiera", expanded=True):
            # Project costs
            costo_total = st.number_input(
                "Costo Total del Proyecto (€)",
                min_value=100000,
                max_value=10000000,
                value=2000000,
                step=50000,
            )
            
            # Team composition and costs
            team_size = st.slider("Tamaño del Equipo", 5, 100, 25)
            consultores = st.slider("Consultores Externos", 0, 20, 5)
            costo_interno = st.number_input(
                "Costo Mensual por Empleado (€)",
                min_value=1000,
                max_value=20000,
                value=5000,
                step=500,
            )
            costo_consultor = st.number_input(
                "Costo Mensual por Consultor (€)",
                min_value=2000,
                max_value=30000,
                value=10000,
                step=500,
            )
            
            # Project duration
            duracion_meses = st.slider(
                "Duración del Proyecto (meses)",
                min_value=3,
                max_value=24,
                value=6,
            )
            
            # Expected benefits
            beneficio_mensual = st.number_input(
                "Beneficio Mensual Esperado (€)",
                min_value=0,
                max_value=1000000,
                value=100000,
                step=10000,
            )

    # Calculate key financial metrics
    costo_equipo_interno = team_size * costo_interno * duracion_meses
    costo_consultores = consultores * costo_consultor * duracion_meses
    costo_total_rrhh = costo_equipo_interno + costo_consultores
    
    # ROI calculation
    beneficio_total = beneficio_mensual * 12  # Anualizado
    inversion_total = costo_total
    roi = ((beneficio_total - inversion_total) / inversion_total) * 100
    
    # Payback period (in months)
    if beneficio_mensual > 0:
        payback_period = inversion_total / beneficio_mensual
    else:
        payback_period = float('inf')

    # Display financial metrics
    st.subheader("📊 Métricas Financieras Clave")
    
    # ROI and Payback metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "ROI Anual",
            f"{roi:.1f}%",
            delta=f"{roi - 100:.1f}%" if roi != 100 else None,
        )
    with col2:
        st.metric(
            "Periodo de Recuperación",
            f"{payback_period:.1f} meses" if payback_period != float('inf') else "N/A",
        )

    # Cost breakdown
    st.subheader("💰 Desglose de Costos")
    
    # Create cost breakdown chart
    cost_data = {
        "Categoría": ["Equipo Interno", "Consultores", "Otros Costos"],
        "Costo": [
            costo_equipo_interno,
            costo_consultores,
            costo_total - costo_total_rrhh,
        ],
    }
    cost_df = pd.DataFrame(cost_data)
    
    # Create a pie chart for cost distribution
    fig = go.Figure(
        data=[
            go.Pie(
                labels=cost_df["Categoría"],
                values=cost_df["Costo"],
                hole=0.4,
                textinfo="label+percent",
                marker=dict(colors=[COLORS["success"], COLORS["warning"], COLORS["danger"]]),
            )
        ]
    )
    
    fig.update_layout(
        title="Distribución de Costos",
        showlegend=True,
        height=400,
        margin=dict(t=30, b=0, l=0, r=0),
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed cost table
    st.markdown("#### 📑 Detalle de Costos")
    cost_details = pd.DataFrame(
        {
            "Concepto": [
                "Equipo Interno",
                "Consultores",
                "Otros Costos",
                "Costo Total",
            ],
            "Monto (€)": [
                costo_equipo_interno,
                costo_consultores,
                costo_total - costo_total_rrhh,
                costo_total,
            ],
            "Porcentaje": [
                costo_equipo_interno / costo_total * 100,
                costo_consultores / costo_total * 100,
                (costo_total - costo_total_rrhh) / costo_total * 100,
                100.0,
            ],
        }
    )
    
    # Format the numbers in the DataFrame
    cost_details["Monto (€)"] = cost_details["Monto (€)"].map("€{:,.0f}".format)
    cost_details["Porcentaje"] = cost_details["Porcentaje"].map("{:.1f}%".format)
    
    st.table(cost_details)
    
    # Financial projections
    st.subheader("📈 Proyecciones Financieras")
    
    # Create monthly projections for the first year
    months = range(1, 13)
    cumulative_cost = [min(m * (costo_total / duracion_meses), costo_total) for m in months]
    cumulative_benefit = [m * beneficio_mensual for m in months]
    net_value = [b - c for b, c in zip(cumulative_benefit, cumulative_cost)]
    
    # Create the projection chart
    fig = go.Figure()
    
    # Add traces
    fig.add_trace(
        go.Scatter(
            x=list(months),
            y=cumulative_cost,
            name="Costos Acumulados",
            line=dict(color=COLORS["danger"], width=2),
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=list(months),
            y=cumulative_benefit,
            name="Beneficios Acumulados",
            line=dict(color=COLORS["success"], width=2),
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=list(months),
            y=net_value,
            name="Valor Neto",
            line=dict(color=COLORS["primary"], width=2, dash="dash"),
        )
    )
    
    # Update layout
    fig.update_layout(
        title="Proyección Financiera a 12 Meses",
        xaxis_title="Mes",
        yaxis_title="Euros (€)",
        showlegend=True,
        height=400,
        margin=dict(t=30, b=0, l=0, r=0),
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Financial alerts
    st.subheader("⚠️ Alertas Financieras")
    
    alerts = []
    if roi < 0:
        alerts.append("🔴 ROI negativo: El proyecto no es rentable en el primer año")
    elif roi < 50:
        alerts.append("🟡 ROI bajo: Considerar optimización de costos")
    
    if payback_period > 12:
        alerts.append("🟡 Periodo de recuperación superior a 1 año")
    
    if (costo_consultores / costo_total) > 0.4:
        alerts.append("🟡 Alto costo en consultores: Considerar internalizar conocimiento")
    
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ Indicadores financieros saludables") 