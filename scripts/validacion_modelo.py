#!/usr/bin/env python3
"""
Script de validación del modelo econométrico Go-Live
Verifica que los cálculos automáticos coincidan con los valores de las tablas temporales
"""

import numpy as np
from datetime import datetime


# --- Modelo econométrico real ---
def quality_model_econometric(
    uat_completion,
    migration_completion,
    e2e_completion,
    training_completion,
    resources_completion,
    hypercare_completion,
):
    """
    Modelo econométrico real: Quality = 1.20 + 0.30·UAT + 0.20·Migration + 0.15·E2E + 0.10·Training + 0.10·Resources + 0.12·Hypercare
    Los valores de completion van de 0 a 1 (0% a 100%)
    """
    return (
        1.20
        + 0.30 * uat_completion
        + 0.20 * migration_completion
        + 0.15 * e2e_completion
        + 0.10 * training_completion
        + 0.10 * resources_completion
        + 0.12 * hypercare_completion
    ) * 100


# --- Valores esperados según las tablas temporales ---
fechas_esperadas = [
    ("2025-08-01", 61.2),  # UAT completado
    ("2025-09-01", 61.7),  # Migration completado
    ("2025-10-01", 76.5),  # E2E completado
    ("2025-11-03", 88.2),  # Training completado + GoLive
    ("2025-12-03", 98.2),  # Post-GoLive con mejora continua
]

# --- Fechas baseline ---
baseline_fechas = {
    "UAT": datetime(2025, 7, 31),
    "Migration": datetime(2025, 8, 31),
    "E2E": datetime(2025, 9, 30),
    "Training": datetime(2025, 10, 31),
    "GoLive": datetime(2025, 11, 3),
}

print("=" * 60)
print("VALIDACIÓN DEL MODELO ECONOMÉTRICO GO-LIVE")
print("=" * 60)

print(
    "\nModelo: Quality = 1.20 + 0.30·UAT + 0.20·Migration + 0.15·E2E + 0.10·Training + 0.10·Resources + 0.12·Hypercare"
)
print("\nCoeficientes:")
print("- Intercepto: 1.20")
print("- UAT: 0.30")
print("- Migration: 0.20")
print("- E2E: 0.15")
print("- Training: 0.10")
print("- Resources: 0.10")
print("- Hypercare: 0.12")

print("\n" + "=" * 60)
print("VERIFICACIÓN DE VALORES ESPERADOS")
print("=" * 60)

for fecha_str, valor_esperado in fechas_esperadas:
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d")

    # Determinar qué fases están completadas en esta fecha
    uat_comp = 1.0 if fecha >= baseline_fechas["UAT"] else 0.0
    migration_comp = 1.0 if fecha >= baseline_fechas["Migration"] else 0.0
    e2e_comp = 1.0 if fecha >= baseline_fechas["E2E"] else 0.0
    training_comp = 1.0 if fecha >= baseline_fechas["Training"] else 0.0
    golive_comp = 1.0 if fecha >= baseline_fechas["GoLive"] else 0.0

    # Resources y Hypercare dependen del progreso general
    resources_comp = (
        uat_comp + migration_comp + e2e_comp + training_comp + golive_comp
    ) / 5.0
    hypercare_comp = golive_comp

    # Calcular calidad usando el modelo
    calidad_calculada = quality_model_econometric(
        uat_comp,
        migration_comp,
        e2e_comp,
        training_comp,
        resources_comp,
        hypercare_comp,
    )

    # Verificar si coincide con el valor esperado
    diferencia = abs(calidad_calculada - valor_esperado)
    status = "✅ CORRECTO" if diferencia < 1.0 else "❌ ERROR"

    print(f"\nFecha: {fecha_str}")
    print(
        f"  Fases completadas: UAT={uat_comp:.1f}, Migration={migration_comp:.1f}, E2E={e2e_comp:.1f}, Training={training_comp:.1f}, GoLive={golive_comp:.1f}"
    )
    print(f"  Resources={resources_comp:.2f}, Hypercare={hypercare_comp:.1f}")
    print(f"  Valor esperado: {valor_esperado:.1f}%")
    print(f"  Valor calculado: {calidad_calculada:.1f}%")
    print(f"  Diferencia: {diferencia:.1f}%")
    print(f"  Status: {status}")

print("\n" + "=" * 60)
print("ANÁLISIS DE SENSIBILIDAD")
print("=" * 60)

# Análisis de sensibilidad para cada variable
variables = ["UAT", "Migration", "E2E", "Training", "Resources", "Hypercare"]
coeficientes = [0.30, 0.20, 0.15, 0.10, 0.10, 0.12]

print("\nImpacto de cada variable en la calidad final:")
for var, coef in zip(variables, coeficientes):
    impacto_100 = coef * 100  # Impacto si la variable pasa de 0% a 100%
    print(f"  {var}: {impacto_100:.1f}% (coeficiente: {coef:.2f})")

print(f"\nCalidad base (todas las variables en 0%): {1.20 * 100:.1f}%")
print(
    f"Calidad máxima (todas las variables en 100%): {quality_model_econometric(1.0, 1.0, 1.0, 1.0, 1.0, 1.0):.1f}%"
)

print("\n" + "=" * 60)
print("SIMULACIÓN DE DELAY EN MIGRATION")
print("=" * 60)

# Simular delay en Migration
print(
    "\nImpacto del delay en Migration (penalización: 1% por día adicional después del día 23):"
)
for delay_days in [0, 1, 3, 5, 10]:
    # Migration con penalización
    migration_comp_penalizada = max(1.0 - (delay_days * 0.01), 0.0)

    # Calcular calidad con penalización
    calidad_con_delay = quality_model_econometric(
        1.0, migration_comp_penalizada, 1.0, 1.0, 1.0, 1.0
    )
    calidad_sin_delay = quality_model_econometric(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)

    impacto = calidad_con_delay - calidad_sin_delay

    print(
        f"  Delay {delay_days} días: Migration={migration_comp_penalizada:.2f}, Calidad={calidad_con_delay:.1f}%, Impacto={impacto:.1f}%"
    )

print("\n" + "=" * 60)
print("VALIDACIÓN COMPLETADA")
print("=" * 60)
