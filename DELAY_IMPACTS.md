# Impacto de Delays en la Calidad del Proyecto

## Tabla de Impactos por Fase

| Fase      | Impacto por Día | Ejemplo 5 días | Ejemplo 10 días | Justificación |
|-----------|----------------|----------------|-----------------|---------------|
| Migration | 0.40% / día    | -2.00%         | -4.00%         | Fase más crítica, impacta directamente en la calidad de todas las fases posteriores. Un retraso aquí tiene el mayor efecto cascada. |
| E2E       | 0.25% / día    | -1.25%         | -2.50%         | Segunda fase más crítica, afecta la validación completa del sistema y la preparación para PRO. |
| UAT       | 0.20% / día    | -1.00%         | -2.00%         | Fase inicial crítica pero con menor impacto cascada que Migration. |
| PRO       | 0.15% / día    | -0.75%         | -1.50%         | Impacto moderado, crítico para el go-live pero con menor efecto en la calidad general. |
| Training  | 0.15% / día    | -0.75%         | -1.50%         | Similar a PRO, afecta la preparación del equipo pero con impacto moderado. |
| Hypercare | 0.10% / día    | -0.50%         | -1.00%         | Menor impacto por día ya que ocurre post go-live. |

## Características del Modelo

1. **Impacto Proporcional**: Los porcentajes de impacto son proporcionales a las ponderaciones del modelo econométrico.

2. **Efecto Acumulativo**: Los delays se acumulan a través de las fases:
   - Un delay en Migration afecta a E2E, PRO, Training y Hypercare
   - Un delay en E2E afecta a PRO, Training y Hypercare
   - etc.

3. **Factores de Riesgo**: Los delays interactúan con los factores de riesgo:
   - Migration: 40% sensibilidad al riesgo
   - PRO: 35% sensibilidad al riesgo
   - UAT: 25% sensibilidad al riesgo
   - Otros: 20% sensibilidad al riesgo

## Ejemplo de Impacto Acumulado

Si tenemos delays en múltiples fases:
- Migration: 5 días (-2.00%)
- E2E: 3 días (-0.75%)
- PRO: 2 días (-0.30%)

**Impacto Total**: -3.05% en la calidad del proyecto para el go-live del 3 de noviembre.

## Notas Importantes

1. Los impactos son más severos en las fases tempranas debido al efecto cascada.
2. El modelo considera la interdependencia entre fases.
3. Los porcentajes son acumulativos pero no lineales (usan una curva cuadrática para riesgos).
4. El impacto total está limitado para evitar degradación excesiva de la calidad. 