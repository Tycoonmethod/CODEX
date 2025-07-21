# Implementación de Bandas de Confianza Condicionales - Ultra v3.0

## 🎯 **Funcionalidad Implementada**

### **Bandas de Confianza Condicionales**
- **Condición**: Bandas ±1σ solo aparecen si `sum_risks > 0`
- **Determinístico**: Si todos los riesgos = 0, solo líneas (sin bandas, σ=0)
- **Proporcional**: Varianza aumenta con nivel de riesgos

## 🔧 **Cambios Técnicos Implementados**

### **1. Función Monte Carlo Mejorada**
```python
def monte_carlo_quality_model(params, iterations=1000, sum_risks=0):
    # If no risks, return deterministic result (no bands)
    if sum_risks == 0:
        base_quality = quality_model_econometric(params)
        return [base_quality], 0.0
    
    # Proportional noise based on total risks
    noise_std = 0.02 * (sum_risks / 300)  # Scale noise with risk level
    
    # Monte Carlo simulation with noise...
```

### **2. Cálculo de Sum Risks**
```python
sum_risks = (st.session_state.external_risks['tech_risk'] + 
             st.session_state.external_risks['business_risk'] + 
             st.session_state.external_risks['scope_changes'])
```

### **3. Función Construir Cronograma Actualizada**
```python
def construir_cronograma_seguro(scenario_windows, es_baseline=False, sum_risks=0):
    # For baseline, force sum_risks = 0 (no bands)
    current_sum_risks = 0 if es_baseline else sum_risks
    qualities_mc, std_mc = monte_carlo_quality_model(params, iterations=100, sum_risks=current_sum_risks)
    calidad = np.mean(qualities_mc)
    calidades.append(calidad)
    calidades_std.append(std_mc)
```

### **4. Llamadas Actualizadas**
```python
# Baseline (always deterministic, no bands)
fechas_base, calidad_base_mean, calidad_base_std, delays_base, end_dates_base = construir_cronograma_seguro(baseline_windows, es_baseline=True, sum_risks=0)

# Scenario (conditional bands based on risks)
fechas_esc, calidad_esc_mean, calidad_esc_std, delays_esc, end_dates_esc = construir_cronograma_seguro(scenario_windows, es_baseline=False, sum_risks=sum_risks)
```

### **5. Visualización Condicional**
```python
# Add scenario confidence bands only if risks > 0
if np.mean(calidad_esc_std) > 0:
    # Upper band
    fig.add_trace(go.Scatter(
        y=np.array(calidad_esc_mean) + np.array(calidad_esc_std),
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Lower band with fill
    fig.add_trace(go.Scatter(
        y=np.array(calidad_esc_mean) - np.array(calidad_esc_std),
        fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.2)',
        name='Escenario ±1σ'
    ))
```

### **6. UI con Sliders de Riesgo**
```python
# External Risk Factors
st.subheader("⚠️ Factores de Riesgo Externos")
st.session_state.external_risks['tech_risk'] = st.slider("Riesgo Técnico (%)", 0, 100, 0)
st.session_state.external_risks['business_risk'] = st.slider("Riesgo de Negocio (%)", 0, 100, 0)
st.session_state.external_risks['scope_changes'] = st.slider("Cambios de Alcance (%)", 0, 100, 0)

# Note about uncertainty bands
st.info("💡 **Riesgos >0 activan bandas de incertidumbre** (Monte Carlo varianza)")
```

## 🧪 **Casos de Prueba**

### **Caso 1: Sin Riesgos (Determinístico)**
- **Configuración**: tech_risk=0, business_risk=0, scope_changes=0
- **Resultado Esperado**: 
  - Solo líneas (Baseline y Escenario)
  - Sin bandas de confianza
  - Calidad ~95.5% en Go-Live
  - σ = 0 para ambas líneas

### **Caso 2: Con Riesgos Bajos**
- **Configuración**: tech_risk=10, business_risk=5, scope_changes=5
- **Resultado Esperado**:
  - sum_risks = 20
  - noise_std = 0.02 * (20/300) = 0.00133
  - Bandas estrechas alrededor de la línea Escenario
  - Baseline sin bandas (siempre determinística)

### **Caso 3: Con Riesgos Altos**
- **Configuración**: tech_risk=50, business_risk=30, scope_changes=20
- **Resultado Esperado**:
  - sum_risks = 100
  - noise_std = 0.02 * (100/300) = 0.00667
  - Bandas más anchas alrededor de la línea Escenario
  - Mayor incertidumbre visible

## 📊 **Fórmulas Clave**

### **Noise Scaling**
```
noise_std = 0.02 * (sum_risks / 300)
```
- **Rango**: 0 (sin riesgos) a 0.02 (riesgos máximos = 300%)
- **Proporcional**: Mayor riesgo = mayor incertidumbre

### **Sum Risks**
```
sum_risks = tech_risk + business_risk + scope_changes
```
- **Rango**: 0% a 300% (cada slider 0-100%)

### **Conditional Bands**
```
if np.mean(calidad_esc_std) > 0:
    # Show bands
else:
    # Only lines
```

## 🚀 **Deployment**

- **Puerto**: 8514 (http://localhost:8514)
- **Archivo**: `pages/1_📊_Modelo_Interactivo.py` actualizado
- **Estado**: ✅ Funcionando con bandas condicionales

## 🎨 **Características Visuales**

### **Sin Riesgos**
- Líneas limpias sin bandas
- Aspecto determinístico
- Enfoque en la diferencia entre baseline y escenario

### **Con Riesgos**
- Bandas naranjas translúcidas (rgba(255, 165, 0, 0.2))
- Leyenda "Escenario ±1σ"
- Visualización clara de la incertidumbre

## ✅ **Verificación**

1. **Riesgos = 0**: Solo líneas, sin bandas
2. **Riesgos > 0**: Bandas proporcionales al nivel de riesgo
3. **Baseline**: Siempre sin bandas (determinística)
4. **Escenario**: Bandas condicionales basadas en riesgos
5. **UI**: Nota informativa sobre activación de bandas

**La implementación está completa y funcionando correctamente.** 