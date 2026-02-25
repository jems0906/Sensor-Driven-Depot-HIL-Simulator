#!/usr/bin/env python3
"""
Simple launcher for the Depot HIL Simulator Dashboard.
"""

import sys
import os
import subprocess

def main():
    """Launch the dashboard with proper setup."""
    
    # Check if we're in the right directory
    if not os.path.exists('run_sim.py'):
        print("❌ Error: Please run this from the Sensor-Driven Depot HIL Simulator directory")
        sys.exit(1)
    
    # Check if database exists, create some sample data if needed
    if not os.path.exists('depot_simulation.db'):
        print("📊 No simulation data found. Running a quick sample scenario...")
        try:
            subprocess.run([sys.executable, 'run_sim.py', '--scenario', 'normal'], 
                         check=True, timeout=30)
            print("✅ Sample data created!")
        except subprocess.CalledProcessError:
            print("⚠️ Could not create sample data, dashboard will be empty")
        except subprocess.TimeoutExpired:
            print("⚠️ Sample data creation timed out")
    
    print("\n🚀 Starting Depot HIL Simulator Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔍 View real-time simulation data and run scenarios")
    print("\n💡 Tip: Keep this terminal open while using the dashboard")
    print("🛑 Press Ctrl+C to stop the dashboard\n")
    
    try:
        # Launch the Flask dashboard
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard', 'app.py')
        subprocess.run([sys.executable, dashboard_path], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()