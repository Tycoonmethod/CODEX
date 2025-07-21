#!/usr/bin/env python3
"""
Análisis del impacto de Migration en el modelo econométrico
Migration es la fase más crítica y debe tener mayor impacto
"""

import numpy as np
from datetime import datetime, timedelta


# --- MODELO ACTUAL ---
def quality_model_actual(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
):
    """Modelo actual normalizado"""
    valor_original = (
        1.20
        + 0.30 * (uat_pct / 100)
        + 0.20 * (migration_pct / 100)
        + 0.15 * (e2e_pct / 100)
        + 0.10 * (training_pct / 100)
        + 0.10 * (resources_pct / 100)
        + 0.12 * (hypercare_pct / 100)
    )
    return (valor_original / 2.17) * 100


# --- MODELO PROPUESTO CON MIGRATION CRÍTICA ---
def quality_model_migration_critica(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
):
    """
    Modelo propuesto donde Migration tiene mayor impacto crítico
    - Migration bloquea E2E y Training si no está completa
    - Penalización exponencial por delays en Migration
    - Mayor peso en el modelo
    """
    # Migration como multiplicador crítico
    migration_factor = migration_pct / 100

    # Si Migration no está completa, E2E y Training se ven severamente afectados
    if migration_pct < 100:
        e2e_pct = e2e_pct * migration_factor * 0.5  # Reducción severa
        training_pct = training_pct * migration_factor * 0.5  # Reducción severa

    # Modelo con mayor peso para Migration
    valor_original = (
        1.00  # Intercepto reducido
        + 0.25 * (uat_pct / 100)  # UAT: peso reducido
        + 0.40 * (migration_pct / 100)  # Migration: peso aumentado significativamente
        + 0.20 * (e2e_pct / 100)  # E2E: peso aumentado
        + 0.15 * (training_pct / 100)  # Training: peso aumentado
        + 0.10 * (resources_pct / 100)  # Resources: igual
        + 0.10 * (hypercare_pct / 100)  # Hypercare: peso reducido
    )

    # Factor de normalización: 1.00 + 0.25 + 0.40 + 0.20 + 0.15 + 0.10 + 0.10 = 2.20
    return (valor_original / 2.20) * 100


def calcular_completitud_fase(dias_usados, dias_optimos, eficiencia_temporal=1.0):
    """Calcula % de completitud de una fase"""
    eficiencia_dias = min(dias_usados / dias_optimos, 1.0) * 100
    return eficiencia_dias * eficiencia_temporal


print("=" * 80)
print("ANÁLISIS DEL IMPACTO DE MIGRATION EN EL MODELO")
print("=" * 80)

print("\n🚨 PROBLEMA IDENTIFICADO:")
print(
    "Migration es la fase más crítica del proyecto pero tiene poco impacto en el modelo actual"
)

# Baseline
baseline_days = {"UAT": 23, "Migration": 23, "E2E": 30, "Training": 31, "GoLive": 6}

print("\n" + "=" * 80)
print("COMPARACIÓN DE MODELOS - IMPACTO DE DELAYS EN MIGRATION")
print("=" * 80)

print("\nImpacto de delays en Migration:")
print("Días\tModelo Actual\tModelo Propuesto\tDiferencia")
print("-" * 60)

for delay_days in [0, 5, 10, 15, 20, 25, 30]:
    # Cálculo de completitud con penalización
    eficiencia_temporal = max(0.5, 1.0 - (delay_days * 0.03))  # 3% por día

    # Fases base
    uat_pct = 100
    migration_pct = 100 * eficiencia_temporal
    e2e_pct = 100
    training_pct = 100
    resources_pct = (
        uat_pct * 0.2 + migration_pct * 0.4 + e2e_pct * 0.2 + training_pct * 0.2
    )
    hypercare_pct = 0

    # Modelo actual
    calidad_actual = quality_model_actual(
        uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
    )

    # Modelo propuesto
    calidad_propuesta = quality_model_migration_critica(
        uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
    )

    diferencia = calidad_propuesta - calidad_actual

    print(
        f"{delay_days:2d}\t{calidad_actual:6.1f}%\t\t{calidad_propuesta:6.1f}%\t\t{diferencia:6.1f}%"
    )

print("\n" + "=" * 80)
print("ANÁLISIS DE SENSIBILIDAD POR VARIABLE")
print("=" * 80)

print("\nContribución individual de cada fase (modelo actual vs propuesto):")
print("Fase\t\tActual\tPropuesto\tCambio")
print("-" * 50)

# Contribuciones en modelo actual
base_actual = quality_model_actual(0, 0, 0, 0, 0, 0)
contrib_uat_actual = quality_model_actual(100, 0, 0, 0, 0, 0) - base_actual
contrib_mig_actual = quality_model_actual(0, 100, 0, 0, 0, 0) - base_actual
contrib_e2e_actual = quality_model_actual(0, 0, 100, 0, 0, 0) - base_actual
contrib_train_actual = quality_model_actual(0, 0, 0, 100, 0, 0) - base_actual
contrib_hyper_actual = quality_model_actual(0, 0, 0, 0, 0, 100) - base_actual

# Contribuciones en modelo propuesto
base_propuesto = quality_model_migration_critica(0, 0, 0, 0, 0, 0)
contrib_uat_propuesto = (
    quality_model_migration_critica(100, 0, 0, 0, 0, 0) - base_propuesto
)
contrib_mig_propuesto = (
    quality_model_migration_critica(0, 100, 0, 0, 0, 0) - base_propuesto
)
contrib_e2e_propuesto = (
    quality_model_migration_critica(0, 0, 100, 0, 0, 0) - base_propuesto
)
contrib_train_propuesto = (
    quality_model_migration_critica(0, 0, 0, 100, 0, 0) - base_propuesto
)
contrib_hyper_propuesto = (
    quality_model_migration_critica(0, 0, 0, 0, 0, 100) - base_propuesto
)

print(
    f"UAT\t\t{contrib_uat_actual:.1f}%\t{contrib_uat_propuesto:.1f}%\t{contrib_uat_propuesto - contrib_uat_actual:+.1f}%"
)
print(
    f"Migration\t{contrib_mig_actual:.1f}%\t{contrib_mig_propuesto:.1f}%\t{contrib_mig_propuesto - contrib_mig_actual:+.1f}%"
)
print(
    f"E2E\t\t{contrib_e2e_actual:.1f}%\t{contrib_e2e_propuesto:.1f}%\t{contrib_e2e_propuesto - contrib_e2e_actual:+.1f}%"
)
print(
    f"Training\t{contrib_train_actual:.1f}%\t{contrib_train_propuesto:.1f}%\t{contrib_train_propuesto - contrib_train_actual:+.1f}%"
)
print(
    f"Hypercare\t{contrib_hyper_actual:.1f}%\t{contrib_hyper_propuesto:.1f}%\t{contrib_hyper_propuesto - contrib_hyper_actual:+.1f}%"
)

print("\n" + "=" * 80)
print("SIMULACIÓN DE ESCENARIOS CRÍTICOS")
print("=" * 80)

print("\nEscenario 1: Migration al 50% (retraso severo)")
calidad_actual_50 = quality_model_actual(100, 50, 100, 100, 87.5, 0)
calidad_propuesta_50 = quality_model_migration_critica(100, 50, 100, 100, 87.5, 0)
print(f"Modelo actual: {calidad_actual_50:.1f}%")
print(f"Modelo propuesto: {calidad_propuesta_50:.1f}%")
print(f"Diferencia: {calidad_propuesta_50 - calidad_actual_50:.1f}%")

print("\nEscenario 2: Migration al 70% (retraso moderado)")
calidad_actual_70 = quality_model_actual(100, 70, 100, 100, 92, 0)
calidad_propuesta_70 = quality_model_migration_critica(100, 70, 100, 100, 92, 0)
print(f"Modelo actual: {calidad_actual_70:.1f}%")
print(f"Modelo propuesto: {calidad_propuesta_70:.1f}%")
print(f"Diferencia: {calidad_propuesta_70 - calidad_actual_70:.1f}%")

print("\nEscenario 3: Migration al 90% (retraso leve)")
calidad_actual_90 = quality_model_actual(100, 90, 100, 100, 98, 0)
calidad_propuesta_90 = quality_model_migration_critica(100, 90, 100, 100, 98, 0)
print(f"Modelo actual: {calidad_actual_90:.1f}%")
print(f"Modelo propuesto: {calidad_propuesta_90:.1f}%")
print(f"Diferencia: {calidad_propuesta_90 - calidad_actual_90:.1f}%")

print("\n" + "=" * 80)
print("RECOMENDACIONES")
print("=" * 80)

print("\n✅ PROPUESTAS PARA MEJORAR EL MODELO:")
print("1. Aumentar el coeficiente de Migration de 0.20 a 0.40")
print("2. Implementar factor de bloqueo: E2E y Training dependen de Migration")
print("3. Penalización exponencial por delays en Migration")
print("4. Migration como multiplicador crítico del proyecto")
print("5. Reducir peso de UAT y Hypercare para compensar")

print("\n🎯 JUSTIFICACIÓN:")
print("- Migration es la fase que habilita todo el proyecto")
print("- Los datos migrados son críticos para E2E y Training")
print("- Un retraso en Migration impacta todo el cronograma")
print("- El modelo debe reflejar esta criticidad real")

print("\n" + "=" * 80)
print("ANÁLISIS COMPLETADO")
print("=" * 80)
