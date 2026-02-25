"""
Vehicle state management for the Depot HIL Simulator.

This module manages individual vehicle states, positions, and behaviors
within the simulation environment.
"""

import uuid
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from ..database.models import VehicleState


@dataclass
class Vehicle:
    """Represents a vehicle in the simulation."""
    
    vehicle_id: str
    state: VehicleState = VehicleState.APPROACHING
    assigned_spot: Optional[int] = None
    assigned_charger: Optional[int] = None
    charge_level: float = 0.2  # Starting charge level (20%)
    target_charge: float = 0.8  # Target charge level (80%)
    arrival_time: int = 0
    departure_time: Optional[int] = None
    
    @classmethod
    def create_new(cls, arrival_time: int = 0) -> 'Vehicle':
        """Create a new vehicle with generated ID."""
        return cls(
            vehicle_id=str(uuid.uuid4())[:8],
            arrival_time=arrival_time
        )
    
    def is_charging_complete(self) -> bool:
        """Check if vehicle has reached target charge level."""
        return self.charge_level >= self.target_charge
    
    def update_charge(self, charge_rate: float = 0.05):
        """Update vehicle charge level."""
        if self.state == VehicleState.CHARGING:
            self.charge_level = min(1.0, self.charge_level + charge_rate)
    
    def can_depart(self) -> bool:
        """Check if vehicle is ready to depart."""
        return (self.state == VehicleState.CHARGING and 
                self.is_charging_complete())


class VehicleManager:
    """Manages all vehicles in the simulation."""
    
    def __init__(self):
        self.vehicles: dict[str, Vehicle] = {}
        self.vehicle_positions: dict[int, Optional[str]] = {}  # spot_id -> vehicle_id
        
    def add_vehicle(self, vehicle: Vehicle):
        """Add a vehicle to the simulation."""
        self.vehicles[vehicle.vehicle_id] = vehicle
        
    def remove_vehicle(self, vehicle_id: str):
        """Remove a vehicle from the simulation."""
        if vehicle_id in self.vehicles:
            vehicle = self.vehicles[vehicle_id]
            # Free up the spot
            if vehicle.assigned_spot is not None:
                self.vehicle_positions[vehicle.assigned_spot] = None
            del self.vehicles[vehicle_id]
    
    def assign_spot(self, vehicle_id: str, spot_id: int) -> bool:
        """Assign a parking spot to a vehicle."""
        if spot_id in self.vehicle_positions and self.vehicle_positions[spot_id] is not None:
            return False  # Spot already occupied
            
        if vehicle_id in self.vehicles:
            vehicle = self.vehicles[vehicle_id]
            # Free previous spot if any
            if vehicle.assigned_spot is not None:
                self.vehicle_positions[vehicle.assigned_spot] = None
                
            # Assign new spot
            vehicle.assigned_spot = spot_id
            self.vehicle_positions[spot_id] = vehicle_id
            return True
        return False
    
    def free_spot(self, spot_id: int):
        """Free a parking spot."""
        if spot_id in self.vehicle_positions:
            vehicle_id = self.vehicle_positions[spot_id]
            if vehicle_id and vehicle_id in self.vehicles:
                self.vehicles[vehicle_id].assigned_spot = None
            self.vehicle_positions[spot_id] = None
    
    def get_vehicle_at_spot(self, spot_id: int) -> Optional[Vehicle]:
        """Get the vehicle currently at a specific spot."""
        vehicle_id = self.vehicle_positions.get(spot_id)
        if vehicle_id:
            return self.vehicles.get(vehicle_id)
        return None
    
    def get_vehicles_by_state(self, state: VehicleState) -> list[Vehicle]:
        """Get all vehicles in a specific state."""
        return [v for v in self.vehicles.values() if v.state == state]
    
    def update_all_vehicles(self):
        """Update all vehicles for one simulation step."""
        for vehicle in self.vehicles.values():
            vehicle.update_charge()
            
    def get_occupancy_status(self) -> dict[int, bool]:
        """Get current occupancy status of all spots."""
        return {spot_id: vehicle_id is not None 
                for spot_id, vehicle_id in self.vehicle_positions.items()}
    
    def detect_occupancy_conflicts(self) -> list[tuple[int, list[str]]]:
        """Detect spots with conflicting occupancy claims."""
        conflicts = []
        
        # Check for multiple vehicles claiming the same spot
        spot_claims = {}
        for vehicle in self.vehicles.values():
            if vehicle.assigned_spot is not None:
                if vehicle.assigned_spot not in spot_claims:
                    spot_claims[vehicle.assigned_spot] = []
                spot_claims[vehicle.assigned_spot].append(vehicle.vehicle_id)
        
        # Find spots with multiple claims
        for spot_id, vehicle_ids in spot_claims.items():
            if len(vehicle_ids) > 1:
                conflicts.append((spot_id, vehicle_ids))
                
        return conflicts