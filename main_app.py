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
from phase_model import calculate_project_timeline, PHASE_WEIGHTS

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
        st.session_state.compare_scenarios = []  # Initialize as empty list
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = {}
    if "scenario_name" not in st.session_state:
        st.session_state.scenario_name = ""
    if "scenario_windows" not in st.session_state:
        st.session_state.scenario_windows = {}
    if "baseline_windows" not in st.session_state:
        st.session_state.baseline_windows = {}
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
    
    # Scenario Management Section
    st.markdown("### 🔄 Gestión de Escenarios")
    
    # Scenario name input and save button
    scenario_name = st.text_input("Nombre del Escenario", key="scenario_name_sidebar")
    
    # Risk Inputs Section
    st.markdown("### ⚠️ Riesgos de Ejecución")
    
    # Create expanders for each phase's risk
    for phase in ['UAT', 'Migration', 'E2E', 'Training', 'PRO', 'Hypercare']:
        with st.expander(f"🔍 {phase}"):
            st.session_state.risk_values[phase] = st.slider(
                "Riesgo de Ejecución (%)",
                0, 100, 
                value=st.session_state.risk_values[phase],
                help=f"Riesgo específico para la fase {phase}. Un riesgo alto degradará la calidad de esta fase."
            )
    
    # Save current scenario
    if st.button("💾 Guardar Escenario"):
        if not scenario_name:
            st.error("Por favor, ingrese un nombre para el escenario")
        else:
            # Collect current scenario parameters
            current_scenario = {
                'sliders': st.session_state.scenario_windows.copy(),
                'risks': st.session_state.risk_values.copy(),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.scenarios[scenario_name] = current_scenario
            st.success(f"✅ Escenario '{scenario_name}' guardado")
            
    # Show saved scenarios
    if st.session_state.scenarios:
        st.markdown("#### Escenarios Guardados")
        
        # Scenario comparison selector
        st.markdown("##### 📊 Comparar Escenarios")
        st.session_state.compare_scenarios = st.multiselect(
            "Seleccionar escenarios a comparar",
            options=list(st.session_state.scenarios.keys()),
            default=st.session_state.compare_scenarios
        )
        
        st.markdown("##### 💾 Escenarios Disponibles")
        for name, data in st.session_state.scenarios.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**{name}**")
                st.caption(f"Guardado: {data['timestamp']}")
            
            with col2:
                if st.button("📥 Cargar", key=f"load_{name}"):
                    # Update scenario windows with saved values
                    st.session_state.scenario_windows = data['sliders'].copy()
                    st.session_state.risk_values = data['risks'].copy()
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

# Import all the helper functions from ultra_current.py
def to_dt(date_obj):
    """Convert various date types to datetime."""
    if pd.isna(date_obj):
        return None
    try:
        if isinstance(date_obj, (str, np.datetime64)):
            return pd.to_datetime(date_obj).to_pydatetime()
        if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
            return datetime.combine(date_obj, time.min)
        if isinstance(date_obj, datetime):
            return date_obj
        return pd.to_datetime(date_obj).to_pydatetime()
    except (ValueError, TypeError):
        return None

def get_days_between(start_date, end_date):
    """Calculate days between dates, handling various date types."""
    try:
        start = to_dt(start_date)
        end = to_dt(end_date)
        if start is None or end is None:
            return 0
        delta = end - start
        return delta.days
    except (ValueError, TypeError, AttributeError):
        return 0

def add_days(base_date, days):
    """Add days to a date, handling various date types."""
    try:
        base = to_dt(base_date)
        if base is None:
            return None
        return base + timedelta(days=days)
    except (ValueError, TypeError):
        return None

def construir_cronograma(scenario_windows, baseline_windows=None):
    """
    Construye el cronograma del proyecto usando el nuevo modelo de fases.
    
    Args:
        scenario_windows: Dict con fechas start/end del escenario actual
        baseline_windows: Dict con fechas start/end de la línea base
    
    Returns:
        Dict with timeline_df and baseline_df or None if error
    """
    try:
        if baseline_windows is None:
            baseline_windows = scenario_windows
            
        # Preparar parámetros para el modelo
        scenario_params = {}
        baseline_params = {}
        
        for phase in ['UAT', 'Migration', 'E2E', 'Training', 'PRO', 'Hypercare']:
            # Convert dates to datetime
            scenario_start = to_dt(scenario_windows[phase]['start'])
            scenario_end = to_dt(scenario_windows[phase]['end'])
            baseline_start = to_dt(baseline_windows[phase]['start'])
            baseline_end = to_dt(baseline_windows[phase]['end'])
            
            if any(d is None for d in [scenario_start, scenario_end, baseline_start, baseline_end]):
                st.error(f"Invalid dates for phase {phase}")
                return None
                
            scenario_params[phase] = {
                'start': scenario_start,
                'end': scenario_end
            }
            baseline_params[phase] = {
                'start': baseline_start,
                'end': baseline_end
            }
        
        # Calcular timeline con el nuevo modelo
        timeline_df = calculate_project_timeline(
            scenario_params, 
            baseline_params,
            st.session_state.risk_values
        )
        
        if timeline_df is None:
            st.error("Error calculating project timeline")
            return None
            
        baseline_df = calculate_project_timeline(
            baseline_params, 
            baseline_params,
            {phase: 0 for phase in PHASE_WEIGHTS.keys()}  # No risks in baseline
        )
        
        if baseline_df is None:
            st.error("Error calculating baseline timeline")
            return None
        
        return {
            'timeline_df': timeline_df,
            'baseline_df': baseline_df
        }
        
    except Exception as e:
        st.error(f"Error in timeline calculation: {str(e)}")
        return None

def plot_quality_evolution(results, comparison_scenarios=None):
    """
    Generate quality evolution plot.
    
    Args:
        results: Dict con timeline_df y baseline_df del escenario actual
        comparison_scenarios: Dict con escenarios adicionales a comparar
    """
    if results is None or 'timeline_df' not in results or 'baseline_df' not in results:
        st.error("No valid timeline data available")
        return None
        
    timeline_df = results['timeline_df']
    baseline_df = results['baseline_df']
    
    # Crear figura
    fig = go.Figure()
    
    # Línea base
    fig.add_trace(
        go.Scatter(
            x=baseline_df.index,
            y=baseline_df['total_quality'],
            name='Baseline',
            line=dict(color=COLORS['baseline'], width=2, dash='dot'),
            hovertemplate='%{y:.1f}%<extra>Baseline</extra>'
        )
    )
    
    # Escenario actual
    fig.add_trace(
        go.Scatter(
            x=timeline_df.index,
            y=timeline_df['total_quality'],
            name='Escenario Actual',
            line=dict(color=COLORS['primary'], width=2),
            hovertemplate='%{y:.1f}%<extra>Escenario Actual</extra>'
        )
    )
    
    # Escenarios de comparación
    if comparison_scenarios:
        for name, scenario in comparison_scenarios.items():
            comp_results = construir_cronograma(
                scenario['sliders'],
                st.session_state.baseline_windows
            )
            if comp_results and 'timeline_df' in comp_results:
                comp_df = comp_results['timeline_df']
                color = COLORS.get(name, COLORS['secondary'])
                fig.add_trace(
                    go.Scatter(
                        x=comp_df.index,
                        y=comp_df['total_quality'],
                        name=f'Escenario: {name}',
                        line=dict(color=color, width=2, dash='dash'),
                        hovertemplate=f'%{{y:.1f}}%<extra>{name}</extra>'
                    )
                )
    
    # Update layout
    fig.update_layout(
        title='Evolución de la Calidad del Proyecto',
        xaxis_title='Fecha',
        yaxis_title='Calidad (%)',
        showlegend=True,
        height=400,
        margin=dict(t=30, b=0, l=0, r=0),
    )
    
    return fig

def plot_quality_waterfall(timeline_df):
    """
    Generate quality waterfall chart showing quality erosion.
    
    Args:
        timeline_df: DataFrame with quality metrics
    """
    if timeline_df is None:
        st.error("No valid timeline data available")
        return None
        
    try:
        # Get the final row for quality loss calculations
        final_metrics = timeline_df.iloc[-1]
        
        # Prepare data for waterfall chart
        waterfall_data = []
        running_total = 100.0  # Start with theoretical maximum
        
        # Add initial bar
        waterfall_data.append(
            go.Bar(
                name='Calidad Teórica Máxima',
                x=['Inicio'],
                y=[100],
                marker_color=COLORS['success']
            )
        )
        
        # Add quality loss for each phase
        for phase in PHASE_WEIGHTS.keys():
            quality_loss = final_metrics[f'{phase}_quality_loss'] * 100  # Convert to percentage
            if quality_loss > 0:
                waterfall_data.append(
                    go.Bar(
                        name=f'Pérdida en {phase}',
                        x=[phase],
                        y=[-quality_loss],  # Negative to show loss
                        marker_color=COLORS['danger']
                    )
                )
                running_total -= quality_loss
        
        # Add final quality bar
        waterfall_data.append(
            go.Bar(
                name='Calidad Final',
                x=['Final'],
                y=[running_total],
                marker_color=COLORS['primary']
            )
        )
        
        # Create waterfall layout
        fig = go.Figure(data=waterfall_data)
        fig.update_layout(
            title='Análisis de Erosión de Calidad',
            showlegend=False,
            height=400,
            margin=dict(t=30, b=0, l=0, r=0),
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error generating waterfall chart: {str(e)}")
        return None

def display_phase_diagnostics(results, comparison_scenarios=None):
    """
    Muestra la tabla de diagnóstico de fases
    
    Args:
        results: Dict con timeline_df y diagnostics del escenario actual
        comparison_scenarios: Dict con escenarios adicionales a comparar
    """
    df = results['diagnostics']
    
    st.markdown("### 📊 Diagnóstico de Fases")
    
    # Crear tabs para cada escenario
    tabs = ["Escenario Actual"]
    if comparison_scenarios:
        tabs.extend([f"Escenario: {name}" for name in comparison_scenarios.keys()])
    
    tab_selected = st.tabs(tabs)
    
    # Función para mostrar diagnóstico de un escenario
    def show_scenario_diagnostics(diagnostics_df, scenario_name=""):
        # Aplicar formato condicional para la salud
        def color_health(val):
            if val < 70:
                return 'background-color: #ffcdd2'  # Rojo claro
            elif val < 90:
                return 'background-color: #fff9c4'  # Amarillo claro
            return 'background-color: #c8e6c9'  # Verde claro
        
        # Formatear columnas
        display_df = diagnostics_df.copy()
        display_df['Fechas'] = display_df.apply(
            lambda x: f"{x['actual_end']} vs {x['baseline_end']}", axis=1
        )
        display_df['Retraso (Días)'] = display_df['delay_days']
        display_df['Salud (%)'] = display_df['health'].round(1)
        
        # Mostrar tabla con formato
        st.dataframe(
            display_df[['phase', 'Fechas', 'Retraso (Días)', 'Salud (%)']].style
            .apply(lambda x: [color_health(v) if i == 3 else '' 
                            for i, v in enumerate(x)], axis=1)
            .format({'Retraso (Días)': '{:+d}', 'Salud (%)': '{:.1f}%'})
        )
        
        # Mostrar métricas clave
        col1, col2 = st.columns(2)
        with col1:
            avg_health = display_df['health'].mean()
            st.metric(
                "Salud Promedio",
                f"{avg_health:.1f}%"
            )
        with col2:
            total_delay = display_df['delay_days'].sum()
            st.metric(
                "Retraso Total",
                f"{total_delay:+d} días",
                delta=None if total_delay == 0 else f"{total_delay:+d}"
            )
    
    # Mostrar diagnóstico del escenario actual
    with tab_selected[0]:
        show_scenario_diagnostics(df)
    
    # Mostrar diagnósticos de escenarios comparados
    if comparison_scenarios:
        for i, (name, scenario) in enumerate(comparison_scenarios.items(), 1):
            with tab_selected[i]:
                # Calcular diagnóstico para el escenario comparado
                comp_results = construir_cronograma(
                    scenario['sliders'],
                    st.session_state.baseline_windows
                )
                show_scenario_diagnostics(
                    comp_results['diagnostics'],
                    name
                )

def toggle_scenario_comparison(scenario_name):
    """Toggle a scenario for comparison."""
    if scenario_name in st.session_state.compare_scenarios:
        st.session_state.compare_scenarios.remove(scenario_name)  # Changed from discard() to remove()
    else:
        st.session_state.compare_scenarios.append(scenario_name)  # Changed from add() to append()

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

def calculate_delay_days(current_date, end_date):
    """Calculate delay days between two dates, handling various date types."""
    if pd.isna(current_date) or pd.isna(end_date):
        return 0
    
    # Convert to datetime if needed
    if isinstance(current_date, (str, np.datetime64)):
        current_date = pd.to_datetime(current_date).to_pydatetime()
    if isinstance(end_date, (str, np.datetime64)):
        end_date = pd.to_datetime(end_date).to_pydatetime()
    
    # Calculate delay
    delay = (current_date - end_date).days if current_date > end_date else 0
    return delay

def safe_get_value(df, index, column):
    """Safely get a value from a DataFrame, handling missing data."""
    try:
        if df is None or index is None or column not in df.columns:
            return 0.0
        return float(df.loc[index, column])
    except (KeyError, ValueError, TypeError):
        return 0.0

def safe_get_index(df):
    """Safely get index from DataFrame, handling missing data."""
    try:
        if df is None or df.empty:
            return pd.DatetimeIndex([])
        return df.index
    except (AttributeError, TypeError):
        return pd.DatetimeIndex([])

def safe_get_array(df, column):
    """Safely get array from DataFrame column, handling missing data."""
    try:
        if df is None or column not in df.columns:
            return np.array([])
        return df[column].to_numpy()
    except (AttributeError, TypeError):
        return np.array([])

def safe_interpolate(x, xp, fp):
    """Safely interpolate values, handling missing data."""
    try:
        if len(xp) == 0 or len(fp) == 0:
            return 0.0
        return float(np.interp(x, xp, fp))
    except (ValueError, TypeError):
        return 0.0

def safe_get_datetime(date_obj):
    """Safely convert to datetime, handling various types."""
    try:
        if pd.isna(date_obj):
            return None
        if isinstance(date_obj, (str, np.datetime64)):
            return pd.to_datetime(date_obj).to_pydatetime()
        if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
            return datetime.combine(date_obj, time.min)
        if isinstance(date_obj, datetime):
            return date_obj
        return pd.to_datetime(date_obj).to_pydatetime()
    except (ValueError, TypeError):
        return None

def calculate_project_duration(start_date, end_date):
    """Calculate project duration in months, handling various date types."""
    try:
        start = safe_get_datetime(start_date)
        end = safe_get_datetime(end_date)
        if start is None or end is None:
            return 0.0
        delta = end - start
        return float(delta.days) / 30.44  # Average month length
    except (ValueError, TypeError, AttributeError):
        return 0.0

def safe_get_dict_value(d, key, default=None):
    """Safely get value from dictionary, handling missing data."""
    try:
        if d is None or not isinstance(d, dict):
            return default
        return d.get(key, default)
    except (AttributeError, TypeError):
        return default

def safe_get_index_value(index, method='min'):
    """Safely get min/max value from index, handling missing data."""
    try:
        if index is None or len(index) == 0:
            return None
        if method == 'min':
            return index.min()
        if method == 'max':
            return index.max()
        return None
    except (AttributeError, TypeError):
        return None

def safe_get_dataframe(results, key):
    """Safely get DataFrame from results, handling missing data."""
    try:
        if results is None:
            return None
        df = results.get(key)
        if df is None or not isinstance(df, pd.DataFrame):
            return None
        return df
    except (AttributeError, TypeError):
        return None

def safe_get_session_state(key, default=0):
    """Safely get value from session state, handling missing data."""
    try:
        return st.session_state.get(key, default)
    except (AttributeError, TypeError):
        return default

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
        scenario_name = st.text_input("Nombre del Escenario", key="scenario_name_main")
        
        # Save button
        if st.button("💾 Guardar Escenario Actual", use_container_width=True):
            if not scenario_name:
                st.error("Por favor, ingrese un nombre para el escenario")
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
                        if compare and name not in st.session_state.compare_scenarios:
                            st.session_state.compare_scenarios.append(name)
                        elif not compare and name in st.session_state.compare_scenarios:
                            st.session_state.compare_scenarios.remove(name)
                    
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

    # Convert scenario_windows to the format expected by calculate_project_timeline
    st.session_state.scenario_windows = {
        "UAT": {"start": uat_start, "end": uat_end},
        "Migration": {"start": mig_start, "end": mig_end},
        "E2E": {"start": e2e_start, "end": e2e_end},
        "Training": {"start": train_start, "end": train_end},
        "PRO": {"start": pro_start, "end": pro_end},
        "Hypercare": {"start": hyper_start, "end": hyper_end}
    }

    # Initialize baseline_windows if not already set
    if not st.session_state.baseline_windows:
        st.session_state.baseline_windows = {
            "UAT": {"start": datetime(2025, 7, 8), "end": datetime(2025, 7, 31)},
            "Migration": {"start": datetime(2025, 8, 1), "end": datetime(2025, 8, 31)},
            "E2E": {"start": datetime(2025, 9, 1), "end": datetime(2025, 9, 30)},
            "Training": {"start": datetime(2025, 10, 1), "end": datetime(2025, 10, 31)},
            "PRO": {"start": datetime(2025, 10, 1), "end": datetime(2025, 10, 30)},
            "Hypercare": {"start": datetime(2025, 11, 4), "end": datetime(2025, 12, 3)}
        }

    # Calculate sum of risks for conditional bands
    sum_risks = (
        st.session_state.external_risks["tech_risk"]
        + st.session_state.external_risks["business_risk"]
        + st.session_state.external_risks["scope_changes"]
    )

    # Initialize financial variables in session state
    if 'team_size' not in st.session_state:
        st.session_state.team_size = 25
    if 'costo_interno' not in st.session_state:
        st.session_state.costo_interno = 5000
    if 'consultores' not in st.session_state:
        st.session_state.consultores = 5
    if 'costo_consultor' not in st.session_state:
        st.session_state.costo_consultor = 10000
    if 'beneficio_mensual' not in st.session_state:
        st.session_state.beneficio_mensual = 100000

    # In the main UI section where we process the timeline
    try:
        # Calculate timeline using new model
        results = construir_cronograma(
            st.session_state.scenario_windows,
            st.session_state.baseline_windows
        )
        
        if results is None:
            st.error("Failed to calculate project timeline")
        else:
            timeline_df = safe_get_dataframe(results, 'timeline_df')
            baseline_df = safe_get_dataframe(results, 'baseline_df')
            
            if timeline_df is None or baseline_df is None:
                st.error("Invalid timeline data")
            else:
                # Get selected scenarios for comparison
                comparison_scenarios = {
                    name: st.session_state.scenarios[name]
                    for name in st.session_state.compare_scenarios
                    if name in st.session_state.scenarios
                }
                
                # Display quality evolution plot
                st.markdown("### 📈 Evolución de la Calidad del Proyecto")
                timeline_fig = plot_quality_evolution(results, comparison_scenarios)
                if timeline_fig is not None:
                    st.plotly_chart(timeline_fig, use_container_width=True)
                
                # Add waterfall chart
                st.markdown("### 📊 Análisis de Erosión de Calidad")
                waterfall_fig = plot_quality_waterfall(timeline_df)
                if waterfall_fig is not None:
                    st.plotly_chart(waterfall_fig, use_container_width=True)
                
                # --- PUNTO: interpolar calidad en Go-Live ---
                golive_date = datetime(2025, 11, 3)
                
                if golive_date and isinstance(golive_date, (datetime, date)):
                    try:
                        # Convert timestamps to float for interpolation
                        timeline_x = safe_get_index(timeline_df).astype(np.int64) // 10**9
                        baseline_x = safe_get_index(baseline_df).astype(np.int64) // 10**9
                        golive_x = datetime.combine(
                            golive_date if isinstance(golive_date, date) else golive_date.date(),
                            time.min
                        ).timestamp()
                        
                        # Get quality values as numpy arrays
                        timeline_quality = safe_get_array(timeline_df, 'total_quality')
                        baseline_quality = safe_get_array(baseline_df, 'total_quality')
                        
                        # Interpolar calidad en fecha de Go-Live
                        golive_quality = safe_interpolate(
                            golive_x,
                            timeline_x,
                            timeline_quality
                        )
                        
                        baseline_quality = safe_interpolate(
                            golive_x,
                            baseline_x,
                            baseline_quality
                        )
                        
                        quality_delta = golive_quality - baseline_quality
                        
                        # Mostrar métricas de calidad
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Calidad Baseline (Go-Live)", f"{baseline_quality:.1f}%")
                        with col2:
                            st.metric(
                                "Calidad Escenario (Go-Live)",
                                f"{golive_quality:.1f}%",
                                delta=f"{quality_delta:.1f}%",
                            )
                            
                        # Calculate project duration
                        project_start = safe_get_index_value(safe_get_index(timeline_df), 'min')
                        project_end = safe_get_index_value(safe_get_index(timeline_df), 'max')
                        duracion_meses = calculate_project_duration(project_start, project_end)
                        
                        # Get financial parameters from session state
                        team_size = safe_get_session_state('team_size', 25)
                        costo_interno = safe_get_session_state('costo_interno', 5000)
                        consultores = safe_get_session_state('consultores', 5)
                        costo_consultor = safe_get_session_state('costo_consultor', 10000)
                        beneficio_mensual = safe_get_session_state('beneficio_mensual', 100000)
                        
                        # Calculate costs
                        costo_equipo_interno = team_size * costo_interno * duracion_meses
                        costo_consultores = consultores * costo_consultor * duracion_meses
                        costo_total_rrhh = costo_equipo_interno + costo_consultores
                        costo_total = costo_total_rrhh * 1.2  # Add 20% for other costs
                        
                        # ROI calculation
                        beneficio_total = beneficio_mensual * 12  # Annualized
                        inversion_total = costo_total
                        roi = ((beneficio_total - inversion_total) / inversion_total) * 100
                        
                        # Payback period (in months)
                        payback_period = inversion_total / beneficio_mensual if beneficio_mensual > 0 else float('inf')
                        
                    except Exception as e:
                        st.error(f"Error calculating Go-Live metrics: {str(e)}")

    except Exception as e:
        st.error(f"Error in timeline processing: {str(e)}")
        st.code(traceback.format_exc())

elif st.session_state.selected_page == "financiero":
    st.title("💰 Análisis Financiero")
    
    # Input parameters
    with st.sidebar:
        st.subheader("Parámetros Financieros")
        
        # Team costs
        team_size = st.number_input(
            "Tamaño del Equipo Interno",
            min_value=1,
            max_value=50,
            value=10,
        )
        costo_interno = st.number_input(
            "Costo Mensual por Empleado (€)",
            min_value=2000,
            max_value=20000,
            value=5000,
            step=500,
        )
        consultores = st.number_input(
            "Número de Consultores",
            min_value=0,
            max_value=20,
            value=5,
        )
        costo_consultor = st.number_input(
            "Costo Mensual por Consultor (€)",
            min_value=2000,
            max_value=30000,
            value=10000,
            step=500,
        )
        
        # Expected benefits
        beneficio_mensual = st.number_input(
            "Beneficio Mensual Esperado (€)",
            min_value=0,
            max_value=1000000,
            value=100000,
            step=10000,
        )

    try:
        # Calculate timeline using new model
        results = construir_cronograma(
            st.session_state.scenario_windows,
            st.session_state.baseline_windows
        )
        timeline_df = results['timeline_df']
        
        # Calculate project duration in months
        project_start = timeline_df.index.min()
        project_end = timeline_df.index.max()
        duracion_meses = (project_end - project_start).days / 30.44  # Average month length
        
        # Calculate costs
        costo_equipo_interno = team_size * costo_interno * duracion_meses
        costo_consultores = consultores * costo_consultor * duracion_meses
        costo_total_rrhh = costo_equipo_interno + costo_consultores
        costo_total = costo_total_rrhh * 1.2  # Add 20% for other costs
        
        # ROI calculation
        beneficio_total = beneficio_mensual * 12  # Annualized
        inversion_total = costo_total
        roi = ((beneficio_total - inversion_total) / inversion_total) * 100
        
        # Payback period (in months)
        payback_period = inversion_total / beneficio_mensual if beneficio_mensual > 0 else float('inf')
        
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
        
        # Get final quality from timeline
        final_quality = timeline_df['total_quality'].iloc[-1]
        
        alertas = []
        if roi < 0:
            alertas.append("🔴 CRÍTICO: ROI negativo - El proyecto no es rentable en el primer año")
        elif roi < 50:
            alertas.append("🟡 ATENCIÓN: ROI bajo - Considerar optimización de costos")
        
        if payback_period > 12:
            alertas.append("🟡 ATENCIÓN: Periodo de recuperación superior a 1 año")
        
        if (costo_consultores / costo_total) > 0.4:
            alertas.append("🟡 ATENCIÓN: Alto costo en consultores - Considerar internalizar conocimiento")
            
        if final_quality < 80:
            alertas.append("🔴 CRÍTICO: Baja calidad del proyecto puede impactar beneficios esperados")
        
        if alertas:
            for alerta in alertas:
                st.warning(alerta)
        else:
            st.success("✅ Todos los indicadores financieros en rango normal")
            
    except Exception as e:
        st.error(f"Error al calcular métricas financieras: {str(e)}")
        st.code(traceback.format_exc()) 