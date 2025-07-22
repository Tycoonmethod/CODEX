#!/usr/bin/env python3
import subprocess
import sys
import time
import threading
from pyngrok import ngrok, conf
import signal

def run_streamlit():
    """Ejecuta la aplicación Streamlit"""
    cmd = [
        sys.executable, "-m", "streamlit", "run", "main_app.py",
        "--server.headless", "true",
        "--server.port", "8501",
        "--server.address", "localhost"
    ]
    return subprocess.Popen(cmd)

def main():
    print("🚀 Iniciando el modelo interactivo con acceso público...")
    
    # Configurar ngrok
    conf.get_default().auth_token = None  # Usar cuenta gratuita
    
    try:
        # Iniciar Streamlit en un proceso separado
        print("📱 Lanzando Streamlit...")
        streamlit_process = run_streamlit()
        
        # Esperar a que Streamlit se inicie
        time.sleep(5)
        
        # Crear túnel público con ngrok
        print("🌐 Creando túnel público...")
        public_tunnel = ngrok.connect(8501)
        public_url = public_tunnel.public_url
        
        print("\n" + "="*60)
        print("✅ ¡MODELO INTERACTIVO LANZADO EXITOSAMENTE!")
        print("="*60)
        print(f"🌍 URL PÚBLICA: {public_url}")
        print(f"🏠 URL LOCAL: http://localhost:8501")
        print("="*60)
        print("📋 INSTRUCCIONES:")
        print("1. Copia la URL pública en tu navegador")
        print("2. ¡Disfruta del modelo interactivo!")
        print("3. Presiona Ctrl+C para detener el servidor")
        print("="*60)
        
        # Mantener el proceso activo
        def signal_handler(sig, frame):
            print("\n🛑 Deteniendo servidor...")
            streamlit_process.terminate()
            ngrok.kill()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Esperar indefinidamente
        streamlit_process.wait()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Intentando método alternativo...")
        return False
    
    return True

if __name__ == "__main__":
    main()