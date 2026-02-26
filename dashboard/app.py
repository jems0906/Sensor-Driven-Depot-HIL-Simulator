"""
Web dashboard for the Depot HIL Simulator.
Provides real-time visualization and control interface.
"""

import sys
import os
import json
import sqlite3
import subprocess
from datetime import datetime
from typing import Dict, List, Any

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# Add parent directory to Python path to import src modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

try:
    from src.database.models import DatabaseManager
except ImportError:
    # Fallback: create a simple database manager if src module not available
    print("Warning: Could not import DatabaseManager from src, using fallback")

app = Flask(__name__)
app.secret_key = 'depot_hil_simulator_key'

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'depot_simulation.db')


class DashboardAPI:
    """API layer for dashboard data operations."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def get_simulation_runs(self) -> List[Dict]:
        """Get all simulation runs with summary data."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sr.run_id, sr.scenario_name, sr.start_time, sr.end_time, sr.total_steps,
                   COUNT(DISTINCT fe.fault_id) as total_faults,
                   COUNT(CASE WHEN fe.alert_level = 'critical' THEN 1 END) as critical_faults
            FROM simulation_runs sr
            LEFT JOIN simulation_steps ss ON sr.run_id = ss.run_id  
            LEFT JOIN fault_events fe ON ss.step_id = fe.step_id
            GROUP BY sr.run_id
            ORDER BY sr.start_time DESC
        """)
        
        runs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return runs
    
    def get_sensor_timeline(self, run_id: str) -> Dict[str, List]:
        """Get sensor readings timeline for a specific run."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ss.time_step, sr.sensor_name, sr.sensor_type, sr.value, sr.is_fault
            FROM sensor_readings sr
            JOIN simulation_steps ss ON sr.step_id = ss.step_id
            WHERE ss.run_id = ?
            ORDER BY ss.time_step, sr.sensor_name
        """, (run_id,))
        
        readings = cursor.fetchall()
        conn.close()
        
        # Organize by sensor type
        timeline = {
            'gates': {'steps': [], 'sensors': {}},
            'occupancy': {'steps': [], 'sensors': {}}, 
            'chargers': {'steps': [], 'sensors': {}}
        }
        
        steps = set()
        for reading in readings:
            step = reading['time_step']
            sensor_name = reading['sensor_name']
            sensor_type = reading['sensor_type']
            
            steps.add(step)
            
            if sensor_type not in timeline:
                continue
                
            if sensor_name not in timeline[sensor_type]['sensors']:
                timeline[sensor_type]['sensors'][sensor_name] = []
            
            # Convert value based on sensor type
            if sensor_type == 'charger':
                try:
                    value_dict = eval(reading['value']) if isinstance(reading['value'], str) else reading['value']
                    value = 1 if value_dict.get('charging', False) else 0
                except:
                    value = 0
            else:
                value = 1 if reading['value'] else 0
                
            timeline[sensor_type]['sensors'][sensor_name].append({
                'step': step,
                'value': value,
                'is_fault': reading['is_fault']
            })
        
        # Set steps for each sensor type
        sorted_steps = sorted(list(steps))
        for sensor_type in timeline:
            timeline[sensor_type]['steps'] = sorted_steps
        
        return timeline
    
    def get_fault_statistics(self) -> Dict[str, Any]:
        """Get fault statistics across all runs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fault counts by type
        cursor.execute("""
            SELECT fault_type, alert_level, COUNT(*) as count
            FROM fault_events 
            GROUP BY fault_type, alert_level
        """)
        fault_counts = cursor.fetchall()
        
        # Fault detection times (for charger failures)
        cursor.execute("""
            SELECT AVG(detected_at - 30) as avg_detection_time
            FROM fault_events 
            WHERE fault_type = 'charger_failure' AND detected_at >= 30
        """)
        detection_time = cursor.fetchone()[0]
        
        # Recent faults
        cursor.execute("""
            SELECT fe.fault_type, fe.alert_level, fe.description, 
                   fe.detected_at, sr.scenario_name
            FROM fault_events fe
            JOIN simulation_steps ss ON fe.step_id = ss.step_id
            JOIN simulation_runs sr ON ss.run_id = sr.run_id
            ORDER BY sr.start_time DESC, fe.detected_at DESC
            LIMIT 10
        """)
        recent_faults = cursor.fetchall()
        
        conn.close()
        
        return {
            'fault_counts': fault_counts,
            'avg_detection_time': detection_time or 0,
            'recent_faults': recent_faults
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics across scenarios."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT scenario_name, 
                   AVG(total_steps) as avg_steps,
                   COUNT(*) as run_count,
                   AVG(CASE WHEN fe.fault_count IS NULL THEN 0 ELSE fe.fault_count END) as avg_faults
            FROM simulation_runs sr
            LEFT JOIN (
                SELECT ss.run_id, COUNT(*) as fault_count
                FROM fault_events fe
                JOIN simulation_steps ss ON fe.step_id = ss.step_id
                GROUP BY ss.run_id
            ) fe ON sr.run_id = fe.run_id
            GROUP BY scenario_name
        """)
        
        metrics = cursor.fetchall()
        conn.close()
        
        return {
            'scenario_metrics': [
                {
                    'scenario': row[0],
                    'avg_steps': row[1],
                    'run_count': row[2], 
                    'avg_faults': row[3]
                }
                for row in metrics
            ]
        }


# Initialize API
dashboard_api = DashboardAPI()


@app.route('/')
def index():
    """Main dashboard view."""
    runs = dashboard_api.get_simulation_runs()
    fault_stats = dashboard_api.get_fault_statistics()
    performance = dashboard_api.get_performance_metrics()
    
    return render_template('dashboard.html', 
                         runs=runs,
                         fault_stats=fault_stats,
                         performance=performance)


@app.route('/run/<run_id>')
def run_detail(run_id):
    """Detailed view of a specific simulation run."""
    timeline = dashboard_api.get_sensor_timeline(run_id)
    
    # Get run info
    runs = dashboard_api.get_simulation_runs()
    run_info = next((r for r in runs if r['run_id'] == run_id), None)
    
    return render_template('run_detail.html',
                         run_info=run_info,
                         timeline=timeline)


@app.route('/api/timeline/<run_id>')
def api_timeline(run_id):
    """API endpoint for timeline data."""
    timeline = dashboard_api.get_sensor_timeline(run_id)
    return jsonify(timeline)


@app.route('/run_scenario', methods=['POST'])
def run_scenario():
    """Run a new simulation scenario."""
    scenario = request.form.get('scenario', 'normal')
    
    try:
        # Run simulation in background
        cmd = [sys.executable, 'run_sim.py', '--scenario', scenario]
        result = subprocess.run(cmd, 
                              cwd=os.path.dirname(DB_PATH),
                              capture_output=True, 
                              text=True,
                              timeout=60)
        
        if result.returncode == 0:
            flash(f'Scenario "{scenario}" completed successfully!', 'success')
        else:
            flash(f'Scenario "{scenario}" failed: {result.stderr}', 'error')
            
    except subprocess.TimeoutExpired:
        flash(f'Scenario "{scenario}" timed out', 'error')
    except Exception as e:
        flash(f'Error running scenario: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/api/runs')
def api_runs():
    """API endpoint for simulation runs."""
    runs = dashboard_api.get_simulation_runs()
    return jsonify(runs)


@app.route('/api/metrics')
def api_metrics():
    """API endpoint for performance metrics."""
    performance = dashboard_api.get_performance_metrics()
    return jsonify(performance)


if __name__ == '__main__':
    print("🚀 Starting Depot HIL Simulator Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔍 View real-time simulation data and run scenarios")
    
    # Use environment variable for debug mode (False in production)
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 5000))
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)