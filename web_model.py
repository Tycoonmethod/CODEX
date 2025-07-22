#!/usr/bin/env python3
from flask import Flask, render_template_string, request, jsonify
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Template HTML para la interfaz
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Modelo Interactivo Go-Live</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .control-group {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
        }
        input, select, button {
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            border: none;
            border-radius: 5px;
            font-size: 14px;
        }
        button {
            background: #4CAF50;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background: #45a049;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .metric {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .metric h3 {
            margin: 0;
            font-size: 24px;
            color: #4CAF50;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Modelo Interactivo Go-Live</h1>
            <p>Planificación y Análisis de Cronogramas de Proyecto</p>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <h3>📅 Configuración de Fechas</h3>
                <label>Fecha de Inicio:</label>
                <input type="date" id="start_date" value="2025-01-01">
                
                <label>Duración UAT (días):</label>
                <input type="number" id="uat_days" value="15" min="1" max="90">
                
                <label>Duración Migration (días):</label>
                <input type="number" id="migration_days" value="10" min="1" max="60">
            </div>
            
            <div class="control-group">
                <h3>⚠️ Factores de Riesgo</h3>
                <label>Riesgo UAT (%):</label>
                <input type="range" id="risk_uat" min="0" max="50" value="10" oninput="updateRiskDisplay()">
                <span id="risk_uat_display">10%</span>
                
                <label>Riesgo Migration (%):</label>
                <input type="range" id="risk_migration" min="0" max="50" value="15" oninput="updateRiskDisplay()">
                <span id="risk_migration_display">15%</span>
            </div>
            
            <div class="control-group">
                <h3>🎯 Simulación</h3>
                <label>Número de Simulaciones:</label>
                <select id="simulations">
                    <option value="100">100</option>
                    <option value="500" selected>500</option>
                    <option value="1000">1000</option>
                </select>
                
                <button onclick="runSimulation()">🔄 Ejecutar Simulación</button>
                <button onclick="generateReport()">📊 Generar Reporte</button>
            </div>
        </div>
        
        <div class="metrics" id="metrics">
            <div class="metric">
                <h3 id="duration_metric">--</h3>
                <p>Duración Estimada (días)</p>
            </div>
            <div class="metric">
                <h3 id="risk_metric">--</h3>
                <p>Riesgo Total (%)</p>
            </div>
            <div class="metric">
                <h3 id="confidence_metric">--</h3>
                <p>Confianza (%)</p>
            </div>
        </div>
        
        <div class="chart-container">
            <div id="timeline_chart"></div>
        </div>
        
        <div class="chart-container">
            <div id="risk_chart"></div>
        </div>
    </div>

    <script>
        function updateRiskDisplay() {
            document.getElementById('risk_uat_display').textContent = 
                document.getElementById('risk_uat').value + '%';
            document.getElementById('risk_migration_display').textContent = 
                document.getElementById('risk_migration').value + '%';
        }
        
        function runSimulation() {
            const data = {
                start_date: document.getElementById('start_date').value,
                uat_days: parseInt(document.getElementById('uat_days').value),
                migration_days: parseInt(document.getElementById('migration_days').value),
                risk_uat: parseInt(document.getElementById('risk_uat').value),
                risk_migration: parseInt(document.getElementById('risk_migration').value),
                simulations: parseInt(document.getElementById('simulations').value)
            };
            
            fetch('/simulate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                // Actualizar métricas
                document.getElementById('duration_metric').textContent = result.avg_duration;
                document.getElementById('risk_metric').textContent = result.total_risk + '%';
                document.getElementById('confidence_metric').textContent = result.confidence + '%';
                
                // Actualizar gráficos
                Plotly.newPlot('timeline_chart', result.timeline_chart.data, result.timeline_chart.layout);
                Plotly.newPlot('risk_chart', result.risk_chart.data, result.risk_chart.layout);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error en la simulación. Revisa la consola.');
            });
        }
        
        function generateReport() {
            alert('📊 Reporte generado! (Funcionalidad en desarrollo)');
        }
        
        // Ejecutar simulación inicial
        window.onload = function() {
            runSimulation();
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        data = request.json
        
        # Extraer parámetros
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        uat_days = data['uat_days']
        migration_days = data['migration_days']
        risk_uat = data['risk_uat']
        risk_migration = data['risk_migration']
        n_simulations = data['simulations']
        
        # Simulación Monte Carlo simplificada
        np.random.seed(42)
        uat_durations = np.random.normal(uat_days, uat_days * risk_uat / 100, n_simulations)
        migration_durations = np.random.normal(migration_days, migration_days * risk_migration / 100, n_simulations)
        
        total_durations = uat_durations + migration_durations
        avg_duration = int(np.mean(total_durations))
        
        # Cálculos de riesgo
        total_risk = int((risk_uat + risk_migration) / 2)
        confidence = max(10, 100 - total_risk)
        
        # Crear gráfico de cronograma
        phases = ['UAT', 'Migration', 'Go-Live']
        starts = [0, uat_days, uat_days + migration_days]
        durations = [uat_days, migration_days, 1]
        
        timeline_fig = go.Figure(data=[
            go.Bar(
                x=durations,
                y=phases,
                orientation='h',
                marker=dict(color=['#FF6B6B', '#4ECDC4', '#45B7D1']),
                text=[f'{d} días' for d in durations],
                textposition='inside'
            )
        ])
        
        timeline_fig.update_layout(
            title='📅 Cronograma del Proyecto',
            xaxis_title='Duración (días)',
            yaxis_title='Fases',
            height=300,
            plot_bgcolor='white'
        )
        
        # Crear gráfico de distribución de riesgo
        risk_fig = go.Figure(data=[
            go.Histogram(
                x=total_durations,
                nbinsx=30,
                marker=dict(color='rgba(255, 107, 107, 0.7)'),
                name='Distribución de Duración'
            )
        ])
        
        risk_fig.update_layout(
            title='📊 Distribución de Riesgo (Monte Carlo)',
            xaxis_title='Duración Total (días)',
            yaxis_title='Frecuencia',
            height=300,
            plot_bgcolor='white'
        )
        
        return jsonify({
            'avg_duration': avg_duration,
            'total_risk': total_risk,
            'confidence': confidence,
            'timeline_chart': {
                'data': json.loads(plotly.utils.PlotlyJSONEncoder().encode(timeline_fig.data)),
                'layout': json.loads(plotly.utils.PlotlyJSONEncoder().encode(timeline_fig.layout))
            },
            'risk_chart': {
                'data': json.loads(plotly.utils.PlotlyJSONEncoder().encode(risk_fig.data)),
                'layout': json.loads(plotly.utils.PlotlyJSONEncoder().encode(risk_fig.layout))
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Iniciando Modelo Interactivo Go-Live...")
    print("="*50)
    print("🌐 Servidor iniciado en: http://localhost:5000")
    print("📱 Abre tu navegador y ve a la URL")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)