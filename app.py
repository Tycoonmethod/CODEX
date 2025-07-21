import streamlit as st
from translations import TEXT, LANGUAGES

# Configuración inicial de la página
st.set_page_config(
    page_title="Modelo Go-Live",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización de variables de sesión
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.lang = 'es'

# Selector de idioma
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

# Título y descripción
st.title(TEXT[st.session_state.lang]['title'])
st.markdown(TEXT[st.session_state.lang]['description'])
st.info(TEXT[st.session_state.lang]['welcome_info'])

# Mostrar las páginas disponibles
st.markdown(f"**- {TEXT[st.session_state.lang]['page1_name']}:** {TEXT[st.session_state.lang]['page1_desc']}")
st.markdown(f"**- {TEXT[st.session_state.lang]['page2_name']}:** {TEXT[st.session_state.lang]['page2_desc']}")
st.markdown(f"**- {TEXT[st.session_state.lang]['page3_name']}:** {TEXT[st.session_state.lang]['page3_desc']}")

st.markdown(TEXT[st.session_state.lang]['select_page_prompt'])
