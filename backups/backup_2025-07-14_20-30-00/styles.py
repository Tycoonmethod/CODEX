import streamlit as st

# Color palette
COLORS = {
    "baseline": "#5AA9E6",  # Ice blue
    "scenario": "#FFA500",  # Warm orange
    "phases": "#B57EDC",  # Soft purple
    "golive": "#FF4C4C",  # Tomato red
    "success": "#28a745",  # Green
    "warning": "#ffc107",  # Yellow
    "danger": "#dc3545",  # Red
    "text": "#F8F9FA",  # Light text
    "muted": "#6C757D",  # Muted text
    "band": "rgba(255, 165, 0, 0.2)",  # Transparent orange for bands
}

# Plot layout configuration
PLOT_LAYOUT = {
    "margin": dict(t=50, b=50, l=50, r=50),
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": dict(family="system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif")
}

# Card styles
CARD_STYLE = """
<style>
    /* Base font family for consistency */
    * {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    div.card {
        border-radius: 10px;
        padding: 1.5rem;
        background: rgba(49, 51, 63, 0.7);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border: 1px solid rgba(250, 250, 250, 0.1);
    }
    div.card-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #F8F9FA;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    div.metric-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    div.metric-label {
        font-size: 0.875rem;
        color: #ffffff !important;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-weight: 400;
    }
    div.metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: #F8F9FA;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    div.phase-bar {
        height: 8px;
        border-radius: 4px;
        margin: 4px 0;
    }
    div.phase-bar-container {
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    div.phase-bar-label {
        min-width: 100px;
        font-size: 0.875rem;
        color: #ffffff !important;
        margin-right: 1rem;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    div.toast {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 1rem;
        background: rgba(49, 51, 63, 0.95);
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    }
    @keyframes slideIn {
        from { transform: translateX(100%); }
        to { transform: translateX(0); }
    }
    
    /* Consistent button styling */
    .stButton > button {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Slider styling */
    .stSlider > div > div {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Plotly chart text consistency */
    .js-plotly-plot .plotly .main-svg {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }
    
    /* Monte Carlo specific styling */
    .monte-carlo-results {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    .monte-carlo-results .metric-label {
        font-size: 0.875rem;
        font-weight: 400;
        color: #ffffff;
    }
    
    .monte-carlo-results .metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: #F8F9FA;
    }
    
    /* Forzar etiquetas de fases en blanco */
    .fase-label,
    .phase-label,
    #estado-de-fases .fase-label,
    #estado-de-fases .phase-label,
    [data-testid="stSidebar"] .fase-label,
    [data-testid="stSidebar"] .phase-label {
        color: #ffffff !important;
    }
    
    /* Para elementos SVG si los hubiera */
    #estado-de-fases text,
    .fase-label text,
    .phase-label text {
        fill: #ffffff !important;
    }
    
    /* Forzar texto en blanco para Go-Live card */
    .card .card-title,
    .card .metric-label,
    .card .metric-value,
    .card .metric-container {
        color: #ffffff !important;
    }
    
    /* Específico para Go-Live */
    .card:has(.card-title:contains("Go-Live")) .card-title,
    .card:has(.card-title:contains("Go-Live")) .metric-label,
    .card:has(.card-title:contains("Go-Live")) .metric-value {
        color: #ffffff !important;
    }
    
    /* Forzar texto en blanco para tabla de Análisis de Retrasos */
    .card table,
    .card table th,
    .card table td,
    .card table thead,
    .card table tbody,
    .card table tr {
        color: #ffffff !important;
    }
    
    /* Específico para Análisis de Retrasos */
    .card:has(.card-title:contains("Análisis de Retrasos")) table,
    .card:has(.card-title:contains("Análisis de Retrasos")) th,
    .card:has(.card-title:contains("Análisis de Retrasos")) td {
        color: #ffffff !important;
    }
    
    /* Forzar texto en blanco para toast notifications (popup de cambio de calidad) */
    .toast,
    .toast .message,
    .toast .value {
        color: #ffffff !important;
    }
    
    /* Si el texto del toast está dentro de un SVG <text> */
    .toast text {
        fill: #ffffff !important;
    }
    
    /* Ensure all text elements use consistent font */
    h1, h2, h3, h4, h5, h6, p, div, span, label {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }
    
    /* Streamlit specific overrides */
    .stMarkdown, .stText, .stTitle, .stHeader, .stSubheader {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }
</style>
"""


def inject_custom_css():
    """Inject custom CSS into the Streamlit app"""
    st.markdown(CARD_STYLE, unsafe_allow_html=True)


def card(title, content):
    """Render a styled card with title and content"""
    return f"""
    <div class="card">
        <div class="card-title">{title}</div>
        {content}
    </div>
    """


def metric(label, value, delta=None):
    """Render a metric with optional delta"""
    delta_html = (
        f'<span style="color: {"#28a745" if float(delta) >= 0 else "#dc3545"}">({delta:+.1f}%)</span>'
        if delta is not None
        else ""
    )
    return f"""
    <div class="metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value} {delta_html}</div>
    </div>
    """


def phase_bar(label, percentage, color):
    """Render a horizontal bar representing phase progress"""
    return f"""
    <div class="phase-bar-container">
        <div class="phase-bar-label">{label}</div>
        <div style="flex-grow: 1;">
            <div class="phase-bar" style="width: {percentage}%; background-color: {color};"></div>
        </div>
        <div style="margin-left: 0.5rem; font-size: 0.875rem; color: #ffffff;">{percentage}%</div>
    </div>
    """


def toast(message, type="info"):
    """Show a toast notification"""
    colors = {
        "info": COLORS["baseline"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["danger"],
    }
    return f"""
    <div class="toast" style="border-left: 4px solid {colors[type]}; color: #ffffff;">
        <span style="color: #ffffff;">{message}</span>
    </div>
    """
