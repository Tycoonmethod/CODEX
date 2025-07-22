#!/usr/bin/env python3
import subprocess
import sys
import time
import webbrowser
from threading import Timer

def launch_streamlit():
    """Lanza Streamlit con configuración optimizada para acceso"""
    print("🚀 Lanzando Modelo Interactivo Go-Live...")
    print("📱 Configurando servidor...")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run", "main_app.py",
        "--server.headless", "false",  # Permitir interfaz
        "--server.port", "8501",
        "--server.address", "0.0.0.0",  # Escuchar en todas las interfaces
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--browser.gatherUsageStats", "false"
    ]
    
    process = subprocess.Popen(cmd)
    
    print("⏳ Esperando que el servidor se inicie...")
    time.sleep(3)
    
    print("\n" + "="*70)
    print("✅ ¡MODELO INTERACTIVO LANZADO EXITOSAMENTE!")
    print("="*70)
    print("🌐 URLs DISPONIBLES:")
    print("   • http://localhost:8501")
    print("   • http://127.0.0.1:8501")
    print("   • http://0.0.0.0:8501")
    print("="*70)
    print("📋 INSTRUCCIONES:")
    print("1. Copia cualquiera de las URLs en tu navegador")
    print("2. Si no funciona, verifica que no haya firewall bloqueando")
    print("3. Presiona Ctrl+C aquí para detener el servidor")
    print("="*70)
    print("🎯 CARACTERÍSTICAS DEL MODELO:")
    print("   • Planificación de cronogramas Go-Live")
    print("   • Análisis de riesgos interactivo")
    print("   • Simulaciones Monte Carlo")
    print("   • Generación de reportes")
    print("   • Visualizaciones dinámicas")
    print("="*70)
    
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor...")
        process.terminate()
        print("✅ Servidor detenido")

if __name__ == "__main__":
    launch_streamlit()