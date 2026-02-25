"""
Database models and schema for the Depot HIL Simulator.

This module defines the database schema for logging simulation data,
including simulation runs, sensor values, control actions, and fault events.
"""

import sqlite3
import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class VehicleState(Enum):
    APPROACHING = "approaching"
    WAITING = "waiting"
    ENTERING = "entering"
    PARKING = "parking"
    CHARGING = "charging"
    EXITING = "exiting"
    DEPARTED = "departed"


class FaultType(Enum):
    CHARGER_FAILURE = "charger_failure"
    GATE_STUCK = "gate_stuck"
    SENSOR_NOISE = "sensor_noise"
    OCCUPANCY_CONFLICT = "occupancy_conflict"
    SYSTEM_ERROR = "system_error"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SimulationRun:
    """Represents a complete simulation run."""
    run_id: str
    scenario_name: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime] = None
    total_steps: int = 0
    config: Optional[Dict[str, Any]] = None


@dataclass
class SimulationStep:
    """Represents a single simulation time step."""
    step_id: str
    run_id: str
    time_step: int
    timestamp: datetime.datetime


@dataclass
class SensorReading:
    """Represents a sensor reading at a specific time step."""
    reading_id: str
    step_id: str
    sensor_type: str
    sensor_name: str
    value: Any
    is_fault: bool = False


@dataclass
class ControlAction:
    """Represents a control action taken by the system."""
    action_id: str
    step_id: str
    controller: str
    action_type: str
    target: str
    command: str
    success: bool = True


@dataclass
class FaultEvent:
    """Represents a detected fault or alert."""
    fault_id: str
    step_id: str
    fault_type: FaultType
    alert_level: AlertLevel
    description: str
    affected_component: str
    detected_at: int  # time step when detected
    resolved_at: Optional[int] = None


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, db_path: str = "depot_simulation.db"):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        
    def connect(self):
        """Establish database connection."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            
    def init_schema(self):
        """Initialize database schema."""
        if not self.connection:
            raise RuntimeError("Database not connected")
            
        cursor = self.connection.cursor()
        
        # Create tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                run_id TEXT PRIMARY KEY,
                scenario_name TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                total_steps INTEGER DEFAULT 0,
                config TEXT
            );
            
            CREATE TABLE IF NOT EXISTS simulation_steps (
                step_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                time_step INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
            );
            
            CREATE TABLE IF NOT EXISTS sensor_readings (
                reading_id TEXT PRIMARY KEY,
                step_id TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                sensor_name TEXT NOT NULL,
                value TEXT NOT NULL,
                is_fault BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (step_id) REFERENCES simulation_steps (step_id)
            );
            
            CREATE TABLE IF NOT EXISTS control_actions (
                action_id TEXT PRIMARY KEY,
                step_id TEXT NOT NULL,
                controller TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target TEXT NOT NULL,
                command TEXT NOT NULL,
                success BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (step_id) REFERENCES simulation_steps (step_id)
            );
            
            CREATE TABLE IF NOT EXISTS fault_events (
                fault_id TEXT PRIMARY KEY,
                step_id TEXT NOT NULL,
                fault_type TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                description TEXT NOT NULL,
                affected_component TEXT NOT NULL,
                detected_at INTEGER NOT NULL,
                resolved_at INTEGER,
                FOREIGN KEY (step_id) REFERENCES simulation_steps (step_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_steps_time ON simulation_steps (time_step);
            CREATE INDEX IF NOT EXISTS idx_sensors_step ON sensor_readings (step_id);
            CREATE INDEX IF NOT EXISTS idx_actions_step ON control_actions (step_id);
            CREATE INDEX IF NOT EXISTS idx_faults_step ON fault_events (step_id);
        """)
        
        self.connection.commit()
        
    def insert_simulation_run(self, run: SimulationRun):
        """Insert a new simulation run."""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO simulation_runs 
            (run_id, scenario_name, start_time, end_time, total_steps, config)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run.run_id, run.scenario_name, run.start_time, 
            run.end_time, run.total_steps, str(run.config) if run.config else None
        ))
        self.connection.commit()
        
    def insert_simulation_step(self, step: SimulationStep):
        """Insert a new simulation step."""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO simulation_steps (step_id, run_id, time_step, timestamp)
            VALUES (?, ?, ?, ?)
        """, (step.step_id, step.run_id, step.time_step, step.timestamp))
        self.connection.commit()
        
    def insert_sensor_reading(self, reading: SensorReading):
        """Insert a new sensor reading."""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO sensor_readings 
            (reading_id, step_id, sensor_type, sensor_name, value, is_fault)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            reading.reading_id, reading.step_id, reading.sensor_type,
            reading.sensor_name, str(reading.value), reading.is_fault
        ))
        self.connection.commit()
        
    def insert_control_action(self, action: ControlAction):
        """Insert a new control action."""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO control_actions 
            (action_id, step_id, controller, action_type, target, command, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            action.action_id, action.step_id, action.controller,
            action.action_type, action.target, action.command, action.success
        ))
        self.connection.commit()
        
    def insert_fault_event(self, fault: FaultEvent):
        """Insert a new fault event."""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO fault_events 
            (fault_id, step_id, fault_type, alert_level, description, 
             affected_component, detected_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fault.fault_id, fault.step_id, fault.fault_type.value,
            fault.alert_level.value, fault.description, fault.affected_component,
            fault.detected_at, fault.resolved_at
        ))
        self.connection.commit()
        
    def get_simulation_results(self, run_id: str) -> Dict[str, Any]:
        """Get comprehensive results for a simulation run."""
        cursor = self.connection.cursor()
        
        # Get basic run info
        cursor.execute("SELECT * FROM simulation_runs WHERE run_id = ?", (run_id,))
        run_info = dict(cursor.fetchone())
        
        # Get fault counts by type
        cursor.execute("""
            SELECT fault_type, alert_level, COUNT(*) as count
            FROM fault_events fe
            JOIN simulation_steps ss ON fe.step_id = ss.step_id
            WHERE ss.run_id = ?
            GROUP BY fault_type, alert_level
        """, (run_id,))
        fault_counts = cursor.fetchall()
        
        # Get total sensor readings
        cursor.execute("""
            SELECT COUNT(*) as total_readings
            FROM sensor_readings sr
            JOIN simulation_steps ss ON sr.step_id = ss.step_id
            WHERE ss.run_id = ?
        """, (run_id,))
        total_readings = cursor.fetchone()[0]
        
        return {
            "run_info": run_info,
            "fault_counts": [dict(row) for row in fault_counts],
            "total_readings": total_readings
        }