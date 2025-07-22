#!/usr/bin/env python3
"""
Script de validación del modelo econométrico MEJORADO con Migration crítica
"""

import numpy as np
import datetime as dt
from datetime import timedelta


# --- MODELO MEJORADO CON MIGRATION CRÍTICA ---
def quality_model_econometric(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
):
    """
    Modelo econométrico mejorado donde Migration es verdaderamente crítica
    """
    # Migration como multiplicador crítico
    migration_factor = migration_pct / 100

    # Si Migration no está completa, E2E y Training se ven severamente afectados
    if migration_pct < 100:
        # Factor de bloqueo: E2E y Training dependen críticamante de Migration
        bloqueo_factor = migration_factor * 0.6  # Reducción severa
        e2e_pct = e2e_pct * bloqueo_factor
        training_pct = training_pct * bloqueo_factor

    # Modelo con Migration como fase crítica
    valor_original = (
        1.00  # Intercepto reducido
        + 0.25 * (uat_pct / 100)  # UAT: peso reducido
        + 0.40 * (migration_pct / 100)  # Migration: peso DUPLICADO (crítica)
        + 0.20 * (e2e_pct / 100)  # E2E: peso aumentado
        + 0.15 * (training_pct / 100)  # Training: peso aumentado
        + 0.10 * (resources_pct / 100)  # Resources: igual
        + 0.10 * (hypercare_pct / 100)  # Hypercare: peso reducido
    )

    # Factor de normalización: 1.00 + 0.25 + 0.40 + 0.20 + 0.15 + 0.10 + 0.10 = 2.20
    factor_normalizacion = 2.20

    # Calidad normalizada entre 0% y 100%
    calidad_normalizada = (valor_original / factor_normalizacion) * 100

    return min(max(calidad_normalizada, 0), 100)


def calcular_completitud_fase(dias_usados, dias_optimos, eficiencia_temporal=1.0):
    """Calcula % de completitud de una fase"""
    eficiencia_dias = min(dias_usados / dias_optimos, 1.0) * 100
    return eficiencia_dias * eficiencia_temporal


print("=" * 80)
print("VALIDACIÓN DEL MODELO MEJORADO CON MIGRATION CRÍTICA")
print("=" * 80)

print("\nModelo Mejorado:")
print(
    "Quality = (1.00 + 0.25×UAT + 0.40×Migration + 0.20×E2E* + 0.15×Training* + 0.10×Resources + 0.10×Hypercare) / 2.20 × 100"
)
print("E2E* y Training* se bloquean si Migration < 100%")

print("\nCoeficientes Beta Mejorados:")
print("- Intercepto: 1.00")
print("- UAT: 0.25 (11.4% de impacto)")
print("- Migration: 0.40 (18.2% de impacto) **CRÍTICA - DUPLICADO**")
print("- E2E: 0.20 (9.1% de impacto)")
print("- Training: 0.15 (6.8% de impacto)")
print("- Resources: 0.10 (4.5% de impacto)")
print("- Hypercare: 0.10 (4.5% de impacto)")

print("\n" + "=" * 80)
print("VALIDACIÓN DE NORMALIZACIÓN")
print("=" * 80)

# Verificar rango de calidad
calidad_minima = quality_model_econometric(0, 0, 0, 0, 0, 0)
calidad_maxima = quality_model_econometric(100, 100, 100, 100, 100, 100)

print(f"\nRango de calidad del modelo mejorado:")
print(f"- Calidad mínima (todas las fases en 0%): {calidad_minima:.1f}%")
print(f"- Calidad máxima (todas las fases en 100%): {calidad_maxima:.1f}%")

# Verificar que la calidad máxima sea exactamente 100%
if abs(calidad_maxima - 100.0) < 0.1:
    print("✅ NORMALIZACIÓN CORRECTA: Calidad máxima = 100%")
else:
    print("❌ ERROR EN NORMALIZACIÓN")

print("\n" + "=" * 80)
print("IMPACTO CRÍTICO DE DELAYS EN MIGRATION")
print("=" * 80)

baseline_days = {"UAT": 23, "Migration": 23, "E2E": 30, "Training": 31, "GoLive": 6}

print("\nImpacto SEVERO de delays en Migration:")
print("Delay\tMigration%\tE2E Bloq%\tTrain Bloq%\tCalidad Final")
print("-" * 65)

for delay_days in [0, 5, 10, 15, 20, 25, 30]:
    # Penalización severa: 5% por día
    eficiencia_temporal = max(0.5, 1.0 - (delay_days * 0.05))

    # Fases base
    uat_pct = 100
    migration_pct = 100 * eficiencia_temporal
    e2e_original = 100
    training_original = 100

    # Calcular bloqueo
    if migration_pct < 100:
        migration_factor = migration_pct / 100
        bloqueo_factor = migration_factor * 0.6
        e2e_bloqueado = e2e_original * bloqueo_factor
        training_bloqueado = training_original * bloqueo_factor
    else:
        e2e_bloqueado = e2e_original
        training_bloqueado = training_original

    resources_pct = (
        uat_pct * 0.2
        + migration_pct * 0.4
        + e2e_bloqueado * 0.2
        + training_bloqueado * 0.2
    )
    hypercare_pct = 0

    calidad_final = quality_model_econometric(
        uat_pct,
        migration_pct,
        e2e_bloqueado,
        training_bloqueado,
        resources_pct,
        hypercare_pct,
    )

    print(
        f"{delay_days:2d}\t{migration_pct:6.1f}%\t{e2e_bloqueado:6.1f}%\t{training_bloqueado:6.1f}%\t{calidad_final:6.1f}%"
    )

print("\n" + "=" * 80)
print("ESCENARIO BASELINE CON MODELO MEJORADO")
print("=" * 80)

# Calcular completitud de fases en baseline
uat_pct = 100
migration_pct = 100
e2e_pct = 100
training_pct = 100
resources_pct = 100
hypercare_pct = 0

calidad_golive_baseline = quality_model_econometric(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_pct
)

print(f"\nCompletitud de fases en Go-Live (3 Nov) - Baseline:")
print(f"- UAT: {uat_pct:.1f}%")
print(f"- Migration: {migration_pct:.1f}%")
print(f"- E2E: {e2e_pct:.1f}%")
print(f"- Training: {training_pct:.1f}%")
print(f"- Resources: {resources_pct:.1f}%")
print(f"- Hypercare: {hypercare_pct:.1f}%")

print(
    f"\n🎯 CALIDAD ESPERADA EN GO-LIVE (3 NOV) - BASELINE: {calidad_golive_baseline:.1f}%"
)

print("\n" + "=" * 80)
print("COMPARACIÓN DE CONTRIBUCIONES")
print("=" * 80)

print("\nContribución individual de cada fase:")
base = quality_model_econometric(0, 0, 0, 0, 0, 0)
contrib_uat = quality_model_econometric(100, 0, 0, 0, 0, 0) - base
contrib_migration = quality_model_econometric(0, 100, 0, 0, 0, 0) - base
contrib_e2e = quality_model_econometric(0, 0, 100, 0, 0, 0) - base
contrib_training = quality_model_econometric(0, 0, 0, 100, 0, 0) - base
contrib_resources = quality_model_econometric(0, 0, 0, 0, 100, 0) - base
contrib_hypercare = quality_model_econometric(0, 0, 0, 0, 0, 100) - base

print(f"- UAT: {contrib_uat:.1f}%")
print(f"- Migration: {contrib_migration:.1f}% **CRÍTICA**")
print(f"- E2E: {contrib_e2e:.1f}%")
print(f"- Training: {contrib_training:.1f}%")
print(f"- Resources: {contrib_resources:.1f}%")
print(f"- Hypercare: {contrib_hypercare:.1f}%")

print("\n" + "=" * 80)
print("EVOLUCIÓN TEMPORAL CON HYPERCARE")
print("=" * 80)

# Calidad en diciembre con Hypercare al 100%
hypercare_dic = 100
calidad_diciembre = quality_model_econometric(
    uat_pct, migration_pct, e2e_pct, training_pct, resources_pct, hypercare_dic
)
incremento_hypercare = calidad_diciembre - calidad_golive_baseline

print(f"\nCalidad en Go-Live (3 Nov): {calidad_golive_baseline:.1f}%")
print(f"Calidad en Diciembre (con Hypercare 100%): {calidad_diciembre:.1f}%")
print(f"Incremento por Hypercare: {incremento_hypercare:.1f}%")

print("\n" + "=" * 80)
print("CONCLUSIONES")
print("=" * 80)

print("\n✅ MEJORAS IMPLEMENTADAS:")
print("✅ Migration ahora tiene peso crítico (0.40 vs 0.20 original)")
print("✅ E2E y Training se bloquean si Migration no está completa")
print("✅ Penalización severa: 5% por día de delay en Migration")
print("✅ El modelo refleja la verdadera criticidad de Migration")
print(f"✅ Calidad esperada en Go-Live (baseline): {calidad_golive_baseline:.1f}%")
print(f"✅ Impacto máximo de Migration: {contrib_migration:.1f}%")

print("\n🚨 AHORA MIGRATION ES VERDADERAMENTE CRÍTICA")
print("- Delay de 10 días reduce calidad de ~95% a ~70%")
print("- Bloquea efectivamente E2E y Training")
print("- Refleja la realidad del proyecto")

print("\n" + "=" * 80)
print("VALIDACIÓN COMPLETADA")
print("=" * 80)
