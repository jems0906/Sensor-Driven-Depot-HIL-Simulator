"""
Command-line interface for the Depot HIL Simulator.
"""

import click
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.simulation.engine import SimulationEngine, SimulationConfig
from src.database.models import DatabaseManager


def create_scenario_config(scenario_name: str) -> SimulationConfig:
    """Create simulation configuration for different scenarios."""
    
    if scenario_name == "normal":
        return SimulationConfig(
            num_gates=2,
            num_spots=5,
            num_chargers=3,
            max_steps=50,
            vehicle_arrival_rate=0.3
        )
    
    elif scenario_name == "charger_failure":
        return SimulationConfig(
            num_gates=2,
            num_spots=5,
            num_chargers=3,
            max_steps=80,
            vehicle_arrival_rate=0.4,
            charger_failure_step=30  # Charger fails at step 30
        )
    
    elif scenario_name == "gate_stuck":
        return SimulationConfig(
            num_gates=2,
            num_spots=5,
            num_chargers=3,
            max_steps=60,
            vehicle_arrival_rate=0.3,
            gate_failure_step=20  # Gate gets stuck at step 20
        )
    
    elif scenario_name == "sensor_noise":
        return SimulationConfig(
            num_gates=2,
            num_spots=5,
            num_chargers=3,
            max_steps=50,
            vehicle_arrival_rate=0.3,
            noise_level=0.15  # Higher sensor noise
        )
    
    elif scenario_name == "high_traffic":
        return SimulationConfig(
            num_gates=2,
            num_spots=8,
            num_chargers=6,
            max_steps=100,
            vehicle_arrival_rate=0.8  # High arrival rate
        )
    
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")


def analyze_results(db_manager: DatabaseManager, run_id: str) -> dict:
    """Analyze simulation results and determine pass/fail."""
    results = db_manager.get_simulation_results(run_id)
    
    analysis = {
        "run_id": run_id,
        "total_faults": 0,
        "critical_faults": 0,
        "occupancy_conflicts": 0,
        "charger_failures": 0,
        "gate_failures": 0,
        "passed": True,
        "failure_reasons": []
    }
    
    # Count faults by type
    for fault in results["fault_counts"]:
        fault_type = fault["fault_type"]
        alert_level = fault["alert_level"] 
        count = fault["count"]
        
        analysis["total_faults"] += count
        
        if alert_level == "critical":
            analysis["critical_faults"] += count
            
        if fault_type == "occupancy_conflict":
            analysis["occupancy_conflicts"] += count
            if count > 0:
                analysis["passed"] = False
                analysis["failure_reasons"].append("Occupancy conflicts detected")
                
        elif fault_type == "charger_failure":
            analysis["charger_failures"] += count
            
        elif fault_type == "gate_stuck":
            analysis["gate_failures"] += count
    
    # Additional pass/fail criteria
    if analysis["critical_faults"] > 5:
        analysis["passed"] = False
        analysis["failure_reasons"].append("Too many critical faults")
    
    return analysis


@click.command()
@click.option('--scenario', default='normal', 
              help='Scenario to run: normal, charger_failure, gate_stuck, sensor_noise, high_traffic')
@click.option('--db-file', default='depot_simulation.db',
              help='Database file path')
@click.option('--verbose', is_flag=True, help='Verbose output')
def main(scenario: str, db_file: str, verbose: bool):
    """Run the Depot HIL Simulator."""
    
    try:
        # Initialize database
        db_manager = DatabaseManager(db_file)
        db_manager.connect()
        db_manager.init_schema()
        
        # Create scenario configuration
        config = create_scenario_config(scenario)
        
        # Initialize and run simulation
        if verbose:
            click.echo(f"Starting scenario: {scenario}")
            click.echo(f"Configuration: {config.num_gates} gates, {config.num_spots} spots, {config.num_chargers} chargers")
        
        engine = SimulationEngine(config, db_manager)
        results = engine.run_complete_simulation(scenario)
        
        # Analyze results
        analysis = analyze_results(db_manager, results["run_id"])
        
        # Display results
        click.echo(f"\n=== Simulation Results ===")
        click.echo(f"Scenario: {scenario}")
        click.echo(f"Run ID: {results['run_id']}")
        click.echo(f"Total Steps: {results['total_steps']}")
        click.echo(f"Total Faults: {analysis['total_faults']}")
        
        if verbose:
            click.echo(f"Critical Faults: {analysis['critical_faults']}")
            click.echo(f"Occupancy Conflicts: {analysis['occupancy_conflicts']}")
            click.echo(f"Charger Failures: {analysis['charger_failures']}")
            click.echo(f"Gate Failures: {analysis['gate_failures']}")
        
        # Pass/Fail determination
        if analysis["passed"]:
            click.echo(click.style("RESULT: PASSED ✓", fg='green'))
        else:
            click.echo(click.style("RESULT: FAILED ✗", fg='red'))
            for reason in analysis["failure_reasons"]:
                click.echo(f"  • {reason}")
        
        db_manager.close()
        
    except Exception as e:
        click.echo(f"Error running simulation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()