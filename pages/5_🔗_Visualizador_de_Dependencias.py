import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from phase_model import calculate_health_score, HEALTH_THRESHOLDS
from styles import COLORS
from datetime import datetime, timedelta

# --- UI Configuration ---
st.set_page_config(page_title="Visualizador de Dependencias", layout="wide")

# --- Inicialización del Estado ---
def initialize_state():
    """Inicializa el estado de la sesión con valores por defecto si no existen"""
    defaults = {
        "baseline_windows": {
            phase: {
                'start': start,
                'end': end
            }
            for phase, (start, end) in {
                "UAT": (datetime(2025, 7, 8), datetime(2025, 7, 31)),
                "Migration": (datetime(2025, 8, 1), datetime(2025, 8, 31)),
                "E2E": (datetime(2025, 9, 1), datetime(2025, 9, 30)),
                "Training": (datetime(2025, 10, 1), datetime(2025, 10, 31)),
                "PRO": (datetime(2025, 10, 1), datetime(2025, 10, 30)),
                "Hypercare": (datetime(2025, 11, 3), datetime(2025, 12, 3)),
            }.items()
        }
    }
    
    # Inicializar scenario_windows con los valores de baseline si no existe
    if "scenario_windows" not in st.session_state:
        st.session_state.scenario_windows = defaults["baseline_windows"].copy()
    
    # Inicializar baseline_windows si no existe
    if "baseline_windows" not in st.session_state:
        st.session_state.baseline_windows = defaults["baseline_windows"]
    
    # Inicializar risk_values si no existe
    if "risk_values" not in st.session_state:
        st.session_state.risk_values = {
            "UAT": 0,
            "Migration": 0,
            "E2E": 0,
            "Training": 0,
            "PRO": 0,
            "Hypercare": 0
        }

# Inicializar el estado
initialize_state()

def get_node_color(health_score):
    """Determina el color del nodo basado en el health score"""
    if health_score < HEALTH_THRESHOLDS['critical']:
        return COLORS['danger']
    elif health_score < HEALTH_THRESHOLDS['warning']:
        return COLORS['warning']
    else:
        return COLORS['success']

def get_edge_color(source_health, target_health):
    """Determina el color de la arista basado en la salud de los nodos"""
    avg_health = (source_health + target_health) / 2
    if avg_health < HEALTH_THRESHOLDS['critical']:
        return COLORS['danger']
    elif avg_health < HEALTH_THRESHOLDS['warning']:
        return COLORS['warning']
    else:
        return COLORS['success']

def calculate_phase_health(phase, scenario_windows, baseline_windows):
    """Calcula la salud de una fase específica"""
    try:
        if phase not in scenario_windows or phase not in baseline_windows:
            return 100  # Default health for unknown phases
            
        scenario_end = scenario_windows[phase]['end']
        baseline_end = baseline_windows[phase]['end']
        
        # Calcular delay en días
        delay = max(0, (scenario_end - baseline_end).days)
        
        # Penalización por delay (5% por día, máximo 100%)
        delay_penalty = min(100, delay * 5)
        
        # Health score base (100 - penalización)
        health = max(0, 100 - delay_penalty)
        
        # Ajustar por riesgo si existe
        if phase in st.session_state.risk_values:
            risk_impact = st.session_state.risk_values[phase]
            health = max(0, health - risk_impact)
        
        return health
    except Exception as e:
        st.error(f"Error calculando salud para fase {phase}: {str(e)}")
        return 100  # Valor por defecto en caso de error

# Título
st.title("🔗 Visualizador de Dependencias del Proyecto")

# Descripción
st.markdown("""
Este visualizador muestra las relaciones y dependencias entre las diferentes fases del proyecto.
- El **color** de cada nodo representa su salud actual
- El **tamaño** del nodo indica su importancia en el proyecto
- Las **flechas** muestran el flujo y las dependencias entre fases
- Los **nodos de riesgo** (más pequeños) muestran los riesgos asociados a cada fase
""")

try:
    # Crear nodos para cada fase
    nodes = []
    edges = []

    # Definir el orden de las fases
    phases = ["UAT", "Migration", "E2E", "Training", "PRO", "Hypercare"]

    # Pesos de importancia para el tamaño de los nodos
    phase_weights = {
        "UAT": 25,
        "Migration": 40,  # Fase más crítica
        "E2E": 20,
        "Training": 15,
        "PRO": 10,
        "Hypercare": 10
    }

    # Calcular health scores para cada fase
    phase_health = {}
    for phase in phases:
        health = calculate_phase_health(
            phase, 
            st.session_state.scenario_windows, 
            st.session_state.baseline_windows
        )
        phase_health[phase] = health
        
        # Crear nodo principal para la fase
        nodes.append(
            Node(
                id=phase,
                label=phase,
                size=phase_weights[phase],
                color=get_node_color(health)
            )
        )
        
        # Añadir nodo de riesgo si existe
        if phase in st.session_state.risk_values:
            risk_value = st.session_state.risk_values[phase]
            if risk_value > 0:
                risk_node_id = f"risk_{phase}"
                risk_color = get_node_color(100 - risk_value)  # Invertir para el color
                nodes.append(
                    Node(
                        id=risk_node_id,
                        label=f"Riesgo\n{risk_value}%",
                        size=15,  # Nodos de riesgo más pequeños
                        color=risk_color
                    )
                )
                # Conectar riesgo con su fase
                edges.append(
                    Edge(
                        source=risk_node_id,
                        target=phase,
                        type="CURVE_SMOOTH",
                        color=risk_color
                    )
                )

    # Crear edges para mostrar las dependencias correctas
    # Dependencias base (secuenciales)
    dependencies = [
        ("UAT", "Migration"),
        ("Migration", "E2E"),
        # E2E tiene dos dependientes: PRO y Training
        ("E2E", "PRO"),
        ("E2E", "Training"),
        # Hypercare depende tanto de PRO como de Training
        ("PRO", "Hypercare"),
        ("Training", "Hypercare")
    ]
    
    # Crear edges para cada dependencia
    for source_phase, target_phase in dependencies:
        # Calcular color de la arista basado en la salud de ambos nodos
        edge_color = get_edge_color(
            phase_health[source_phase],
            phase_health[target_phase]
        )
        
        edges.append(
            Edge(
                source=source_phase,
                target=target_phase,
                type="CURVE_SMOOTH",
                color=edge_color
            )
        )

    # Configuración del gráfico
    config = Config(
        width=800,
        height=600,
        directed=True,
        physics=True,
        hierarchical=True,  # Activar layout jerárquico
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=False,
        node={'labelProperty': 'label'},
        link={'labelProperty': 'label', 'renderLabel': True},
        # Configuración específica para el layout jerárquico
        hierarchical_layout={
            'levelSeparation': 150,  # Distancia vertical entre niveles
            'nodeSpacing': 150,      # Distancia horizontal entre nodos
            'treeSpacing': 200,      # Distancia entre subárboles
            'direction': 'UD',       # Up to Down layout
            'sortMethod': 'directed' # Mantener el orden basado en las dependencias
        }
    )

    # Renderizar el gráfico
    agraph(nodes=nodes, edges=edges, config=config)

    # Leyenda
    st.markdown("### 🎯 Leyenda")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Colores de Nodos:**")
        st.markdown(f"🟢 Verde: Saludable (>{HEALTH_THRESHOLDS['warning']}%)")
        st.markdown(f"🟡 Amarillo: En Riesgo ({HEALTH_THRESHOLDS['critical']}-{HEALTH_THRESHOLDS['warning']}%)")
        st.markdown(f"🔴 Rojo: Crítico (<{HEALTH_THRESHOLDS['critical']}%)")

    with col2:
        st.markdown("**Tamaño de Nodos:**")
        st.markdown("⭕ Grande: Fase crítica (Migration)")
        st.markdown("⭕ Mediano: Fases principales")
        st.markdown("⭕ Pequeño: Nodos de riesgo")

    with col3:
        st.markdown("**Conexiones:**")
        st.markdown("➡️ Flecha: Dependencia directa")
        st.markdown("🔄 Color: Salud de la conexión")
        st.markdown("📊 Grosor: Importancia de la dependencia")

    # Información adicional
    st.markdown("### 📝 Notas Importantes")
    st.info("""
    - La fase de **Migration** es la más crítica y tiene el mayor impacto en las fases posteriores
    - **E2E** es un punto de bifurcación que afecta tanto a **PRO** como a **Training**
    - **Hypercare** depende de la finalización exitosa de **PRO** y **Training**
    - Los retrasos en E2E afectan en paralelo a PRO y Training
    - Los riesgos afectan directamente a su fase correspondiente y pueden propagarse
    """)

    # Explicación de las dependencias
    st.markdown("### 🔄 Flujo de Dependencias")
    st.markdown("""
    1. **UAT** → **Migration**: La migración depende de las pruebas de usuario
    2. **Migration** → **E2E**: Las pruebas end-to-end requieren migración completa
    3. **E2E** → **PRO** y **Training**: 
        - PRO necesita validación end-to-end
        - Training también requiere validación end-to-end
    4. **PRO** y **Training** → **Hypercare**:
        - Hypercare solo puede comenzar cuando tanto PRO como Training estén completos
    """)

except Exception as e:
    st.error(f"Error en la visualización: {str(e)}")
    st.error("Por favor, asegúrate de que todas las fases y datos necesarios estén inicializados correctamente.") 