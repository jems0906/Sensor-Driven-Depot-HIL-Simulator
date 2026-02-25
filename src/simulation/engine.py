"""
Main simulation engine for the Depot HIL Simulator.
"""

import uuid
import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from .sensors import SensorNetwork
from .vehicles import Vehicle, VehicleManager, VehicleState
from ..database.models import (
    DatabaseManager, SimulationRun, SimulationStep, 
    SensorReading as DBSensorReading, ControlAction, FaultEvent,
    FaultType, AlertLevel
)
from ..control.depot_controller import DepotController


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    num_gates: int = 2
    num_spots: int = 10
    num_chargers: int = 6
    max_steps: int = 100
    vehicle_arrival_rate: float = 0.3
    charger_failure_step: Optional[int] = None
    gate_failure_step: Optional[int] = None
    noise_level: float = 0.05


class SimulationEngine:
    """Core simulation engine."""
    
    def __init__(self, config: SimulationConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        
        # Initialize components
        self.sensor_network = SensorNetwork(
            config.num_gates, config.num_spots, config.num_chargers
        )
        self.vehicle_manager = VehicleManager()
        self.controller = DepotController(
            config.num_gates, config.num_spots, config.num_chargers
        )
        
        # Simulation state
        self.current_step = 0
        self.run_id = str(uuid.uuid4())
        self.step_id = None
        self.faults_detected = []
        
    def start_simulation(self, scenario_name: str):
        """Start a new simulation run."""
        run = SimulationRun(
            run_id=self.run_id,
            scenario_name=scenario_name,
            start_time=datetime.datetime.now(),
            config=self.config.__dict__
        )
        self.db_manager.insert_simulation_run(run)
        
    def run_step(self) -> Dict:
        """Execute a single simulation step."""
        self.current_step += 1
        self.step_id = f"{self.run_id}_{self.current_step}"
        
        # Create step record
        step = SimulationStep(
            step_id=self.step_id,
            run_id=self.run_id,
            time_step=self.current_step,
            timestamp=datetime.datetime.now()
        )
        self.db_manager.insert_simulation_step(step)
        
        # Inject scenario-specific failures
        self._inject_failures()
        
        # Generate new vehicles
        self._generate_vehicles()
        
        # Read all sensors
        sensor_readings = self.sensor_network.read_all_sensors()
        
        # Log sensor readings
        for reading in sensor_readings.values():
            db_reading = DBSensorReading(
                reading_id=str(uuid.uuid4()),
                step_id=self.step_id,
                sensor_type=reading.sensor_type.value,
                sensor_name=reading.sensor_name,
                value=reading.value,
                is_fault=reading.is_fault
            )
            self.db_manager.insert_sensor_reading(db_reading)
        
        # Update vehicle states
        self.vehicle_manager.update_all_vehicles()
        
        # Run control logic
        control_actions = self.controller.process_step(
            sensor_readings, self.vehicle_manager, self.current_step
        )
        
        # Log control actions
        for action in control_actions:
            self.db_manager.insert_control_action(action)
        
        # Detect faults
        faults = self._detect_faults(sensor_readings)
        
        # Log faults
        for fault in faults:
            self.db_manager.insert_fault_event(fault)
            self.faults_detected.append(fault)
        
        return {
            "step": self.current_step,
            "vehicles": len(self.vehicle_manager.vehicles),
            "sensor_readings": len(sensor_readings),
            "control_actions": len(control_actions),
            "faults": len(faults)
        }
    
    def _generate_vehicles(self):
        """Generate new vehicles based on arrival rate."""
        import random
        if random.random() < self.config.vehicle_arrival_rate:
            vehicle = Vehicle.create_new(self.current_step)
            self.vehicle_manager.add_vehicle(vehicle)
    
    def _inject_failures(self):
        """Inject scenario-specific failures."""
        # Charger failure
        if (self.config.charger_failure_step and 
            self.current_step == self.config.charger_failure_step):
            self.sensor_network.chargers[0].is_failed = True
            
        # Gate failure
        if (self.config.gate_failure_step and 
            self.current_step == self.config.gate_failure_step):
            self.sensor_network.gates[0].is_failed = True
    
    def _detect_faults(self, sensor_readings) -> List[FaultEvent]:
        """Detect faults based on sensor readings and system state."""
        faults = []
        
        # Check for sensor faults
        for reading in sensor_readings.values():
            if reading.is_fault:
                fault = FaultEvent(
                    fault_id=str(uuid.uuid4()),
                    step_id=self.step_id,
                    fault_type=self._classify_fault_type(reading),
                    alert_level=AlertLevel.WARNING,
                    description=f"Sensor fault detected: {reading.sensor_name}",
                    affected_component=reading.sensor_name,
                    detected_at=self.current_step
                )
                faults.append(fault)
        
        # Check for occupancy conflicts
        conflicts = self.vehicle_manager.detect_occupancy_conflicts()
        for spot_id, vehicle_ids in conflicts:
            fault = FaultEvent(
                fault_id=str(uuid.uuid4()),
                step_id=self.step_id,
                fault_type=FaultType.OCCUPANCY_CONFLICT,
                alert_level=AlertLevel.CRITICAL,
                description=f"Multiple vehicles claiming spot {spot_id}: {vehicle_ids}",
                affected_component=f"spot_{spot_id}",
                detected_at=self.current_step
            )
            faults.append(fault)
        
        return faults
    
    def _classify_fault_type(self, reading) -> FaultType:
        """Classify fault type based on sensor reading."""
        if reading.sensor_type.value == "charger":
            return FaultType.CHARGER_FAILURE
        elif reading.sensor_type.value == "gate":
            return FaultType.GATE_STUCK
        else:
            return FaultType.SENSOR_NOISE
    
    def run_complete_simulation(self, scenario_name: str) -> Dict:
        """Run a complete simulation from start to finish."""
        self.start_simulation(scenario_name)
        
        results = []
        for _ in range(self.config.max_steps):
            step_result = self.run_step()
            results.append(step_result)
            
            # Early termination conditions
            if len(self.faults_detected) > 10:  # Too many faults
                break
        
        # Finalize simulation
        self._finalize_simulation()
        
        return {
            "run_id": self.run_id,
            "total_steps": self.current_step,
            "total_faults": len(self.faults_detected),
            "step_results": results
        }
    
    def _finalize_simulation(self):
        """Finalize simulation run."""
        # Update run record
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            UPDATE simulation_runs 
            SET end_time = ?, total_steps = ?
            WHERE run_id = ?
        """, (datetime.datetime.now(), self.current_step, self.run_id))
        self.db_manager.connection.commit()