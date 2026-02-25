"""
Sensor implementations for the Depot HIL Simulator.
"""

import random
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class SensorType(Enum):
    GATE = "gate"
    OCCUPANCY = "occupancy" 
    CHARGER = "charger"


@dataclass
class SensorReading:
    sensor_name: str
    sensor_type: SensorType
    value: Any
    is_fault: bool = False
    noise_level: float = 0.0


class GateSensor:
    """Simulates gate position sensors."""
    
    def __init__(self, gate_id: int, failure_rate: float = 0.01):
        self.gate_id = gate_id
        self.is_open = False
        self.is_failed = False
        self.failure_rate = failure_rate
        
    def read(self) -> SensorReading:
        # Simulate occasional sensor failures
        if random.random() < self.failure_rate:
            self.is_failed = True
            
        return SensorReading(
            sensor_name=f"gate_{self.gate_id}",
            sensor_type=SensorType.GATE,
            value=self.is_open and not self.is_failed,
            is_fault=self.is_failed
        )
    
    def set_state(self, is_open: bool):
        """Set gate state (used by control system)."""
        if not self.is_failed:
            self.is_open = is_open


class OccupancySensor:
    """Simulates parking spot occupancy sensors."""
    
    def __init__(self, spot_id: int, noise_rate: float = 0.05):
        self.spot_id = spot_id
        self.is_occupied = False
        self.noise_rate = noise_rate
        
    def read(self) -> SensorReading:
        # Add sensor noise
        noise = random.random() < self.noise_rate
        actual_reading = self.is_occupied
        
        if noise:
            actual_reading = not actual_reading
            
        return SensorReading(
            sensor_name=f"spot_{self.spot_id}",
            sensor_type=SensorType.OCCUPANCY,
            value=actual_reading,
            is_fault=noise,
            noise_level=self.noise_rate
        )
    
    def set_occupancy(self, occupied: bool):
        """Set actual occupancy state."""
        self.is_occupied = occupied


class ChargerSensor:
    """Simulates EV charger sensors."""
    
    def __init__(self, charger_id: int, failure_rate: float = 0.02):
        self.charger_id = charger_id
        self.is_connected = False
        self.is_charging = False
        self.is_failed = False
        self.failure_rate = failure_rate
        self.power_output = 0.0
        
    def read(self) -> SensorReading:
        # Simulate charger failures
        if random.random() < self.failure_rate:
            self.is_failed = True
            self.is_charging = False
            self.power_output = 0.0
            
        status = {
            "connected": self.is_connected,
            "charging": self.is_charging and not self.is_failed,
            "power_kw": self.power_output if not self.is_failed else 0.0,
            "failed": self.is_failed
        }
        
        return SensorReading(
            sensor_name=f"charger_{self.charger_id}",
            sensor_type=SensorType.CHARGER,
            value=status,
            is_fault=self.is_failed
        )
    
    def connect_vehicle(self):
        """Vehicle connects to charger."""
        self.is_connected = True
        
    def disconnect_vehicle(self):
        """Vehicle disconnects from charger."""
        self.is_connected = False
        self.is_charging = False
        self.power_output = 0.0
        
    def start_charging(self, power_kw: float = 50.0):
        """Start charging (if not failed)."""
        if not self.is_failed and self.is_connected:
            self.is_charging = True
            self.power_output = power_kw
            
    def stop_charging(self):
        """Stop charging."""
        self.is_charging = False
        self.power_output = 0.0


class SensorNetwork:
    """Manages all sensors in the depot."""
    
    def __init__(self, num_gates: int = 2, num_spots: int = 10, num_chargers: int = 6):
        self.gates = {i: GateSensor(i) for i in range(num_gates)}
        self.occupancy_sensors = {i: OccupancySensor(i) for i in range(num_spots)}
        self.chargers = {i: ChargerSensor(i) for i in range(num_chargers)}
        
    def read_all_sensors(self) -> Dict[str, SensorReading]:
        """Read all sensors and return combined readings."""
        readings = {}
        
        # Read gate sensors
        for gate_id, sensor in self.gates.items():
            reading = sensor.read()
            readings[reading.sensor_name] = reading
            
        # Read occupancy sensors
        for spot_id, sensor in self.occupancy_sensors.items():
            reading = sensor.read()
            readings[reading.sensor_name] = reading
            
        # Read charger sensors
        for charger_id, sensor in self.chargers.items():
            reading = sensor.read()
            readings[reading.sensor_name] = reading
            
        return readings
    
    def get_sensor(self, sensor_name: str):
        """Get sensor by name."""
        if sensor_name.startswith("gate_"):
            gate_id = int(sensor_name.split("_")[1])
            return self.gates.get(gate_id)
        elif sensor_name.startswith("spot_"):
            spot_id = int(sensor_name.split("_")[1])
            return self.occupancy_sensors.get(spot_id)
        elif sensor_name.startswith("charger_"):
            charger_id = int(sensor_name.split("_")[1])
            return self.chargers.get(charger_id)
        return None
        
    def inject_fault(self, sensor_name: str, fault_type: str = "failure"):
        """Inject a fault into a specific sensor."""
        sensor = self.get_sensor(sensor_name)
        if sensor:
            if hasattr(sensor, 'is_failed'):
                sensor.is_failed = True