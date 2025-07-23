#!/usr/bin/env python3
"""
Script de prueba para verificar que la corrección del error funciona
"""

from datetime import datetime, date, time, timedelta

def to_dt(x):
    """Convierte date o datetime.date en datetime.datetime a las 00:00h"""
    if x is None:
        return datetime.now()
    if isinstance(x, datetime):
        return x
    if isinstance(x, date):
        return datetime.combine(x, time(0, 0))
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x)
    return x

# Prueba específica del error
print("=== PRUEBA DEL ERROR ESPECÍFICO ===")

# Simular exactamente la línea que causa el error
dt1 = datetime(2025, 11, 3)
dt2 = datetime.now().date()

print(f"dt1: {dt1} (type: {type(dt1)})")
print(f"dt2: {dt2} (type: {type(dt2)})")

# Convertir usando to_dt
converted_dt1 = to_dt(dt1)
converted_dt2 = to_dt(dt2)

print(f"converted_dt1: {converted_dt1} (type: {type(converted_dt1)})")
print(f"converted_dt2: {converted_dt2} (type: {type(converted_dt2)})")

# Calcular la diferencia
try:
    days_diff = (converted_dt1 - converted_dt2).days
    print(f"✅ Días de diferencia: {days_diff}")
    print("✅ ¡Error corregido exitosamente!")
except Exception as e:
    print(f"❌ Error: {e}")
    print("❌ La corrección no funcionó")