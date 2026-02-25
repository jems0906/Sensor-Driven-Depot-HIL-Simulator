"""
Main depot controller - implements control logic for the HIL simulator.
"""

import uuid
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..database.models import ControlAction, VehicleState
from ..simulation.vehicles import VehicleManager, Vehicle


@dataclass
class DepotState:
    """Current state of the depot."""
    available_spots: List[int]
    available_chargers: List[int]
    gate_states: Dict[int, bool]  # gate_id -> is_open
    spot_occupancy: Dict[int, bool]  # spot_id -> occupied
    charger_status: Dict[int, Dict]  # charger_id -> status


class DepotController:
    """Main control logic for depot operations."""
    
    def __init__(self, num_gates: int, num_spots: int, num_chargers: int):
        self.num_gates = num_gates
        self.num_spots = num_spots  
        self.num_chargers = num_chargers
        
        # Initialize depot state
        self.depot_state = DepotState(
            available_spots=list(range(num_spots)),
            available_chargers=list(range(num_chargers)),
            gate_states={i: False for i in range(num_gates)},
            spot_occupancy={i: False for i in range(num_spots)},
            charger_status={i: {"connected": False, "charging": False} for i in range(num_chargers)}
        )
    
    def process_step(self, sensor_readings: Dict, vehicle_manager: VehicleManager, 
                    current_step: int) -> List[ControlAction]:
        """Process one control step."""
        actions = []
        
        # Update depot state from sensor readings
        self._update_depot_state(sensor_readings)
        
        # Process each vehicle
        for vehicle in vehicle_manager.vehicles.values():
            vehicle_actions = self._process_vehicle(vehicle, vehicle_manager, current_step)
            actions.extend(vehicle_actions)
        
        # Gate control logic
        gate_actions = self._control_gates(vehicle_manager, current_step)
        actions.extend(gate_actions)
        
        return actions
    
    def _update_depot_state(self, sensor_readings: Dict):
        """Update depot state based on sensor readings."""
        for sensor_name, reading in sensor_readings.items():
            if sensor_name.startswith("gate_"):
                gate_id = int(sensor_name.split("_")[1])
                self.depot_state.gate_states[gate_id] = reading.value
                
            elif sensor_name.startswith("spot_"):
                spot_id = int(sensor_name.split("_")[1])
                self.depot_state.spot_occupancy[spot_id] = reading.value
                
            elif sensor_name.startswith("charger_"):
                charger_id = int(sensor_name.split("_")[1])
                if isinstance(reading.value, dict):
                    self.depot_state.charger_status[charger_id] = reading.value
    
    def _process_vehicle(self, vehicle: Vehicle, vehicle_manager: VehicleManager, 
                        current_step: int) -> List[ControlAction]:
        """Process control logic for a single vehicle."""
        actions = []
        
        if vehicle.state == VehicleState.APPROACHING:
            # Check if we can let vehicle enter
            if self._can_admit_vehicle():
                spot = self._assign_parking_spot(vehicle, vehicle_manager)
                if spot is not None:
                    vehicle.state = VehicleState.ENTERING
                    actions.append(self._create_action(
                        "depot_controller", "vehicle_assignment", 
                        f"vehicle_{vehicle.vehicle_id}", f"assign_spot_{spot}", current_step
                    ))
                else:
                    vehicle.state = VehicleState.WAITING
                    
        elif vehicle.state == VehicleState.ENTERING:
            # Vehicle is entering, move to parking
            vehicle.state = VehicleState.PARKING
            
        elif vehicle.state == VehicleState.PARKING:
            # Vehicle has parked, try to assign charger
            charger = self._assign_charger(vehicle)
            if charger is not None:
                vehicle.assigned_charger = charger
                vehicle.state = VehicleState.CHARGING
                actions.append(self._create_action(
                    "depot_controller", "charger_assignment",
                    f"charger_{charger}", "start_charging", current_step
                ))
                
        elif vehicle.state == VehicleState.CHARGING:
            # Check if charging is complete or charger failed
            if vehicle.can_depart():
                vehicle.state = VehicleState.EXITING
                if vehicle.assigned_charger is not None:
                    actions.append(self._create_action(
                        "depot_controller", "charger_control",
                        f"charger_{vehicle.assigned_charger}", "stop_charging", current_step
                    ))
            elif self._is_charger_failed(vehicle.assigned_charger):
                vehicle.state = VehicleState.WAITING
                actions.append(self._create_action(
                    "depot_controller", "fault_response",
                    f"vehicle_{vehicle.vehicle_id}", "charger_failure_detected", current_step
                ))
                
        elif vehicle.state == VehicleState.EXITING:
            # Vehicle is leaving
            self._free_vehicle_resources(vehicle, vehicle_manager)
            vehicle.state = VehicleState.DEPARTED
            vehicle.departure_time = current_step
            
        return actions
    
    def _can_admit_vehicle(self) -> bool:
        """Check if depot can admit a new vehicle."""
        # Need at least one available spot and one working charger
        available_spots = sum(1 for occupied in self.depot_state.spot_occupancy.values() if not occupied)
        working_chargers = sum(1 for status in self.depot_state.charger_status.values() 
                              if not status.get("failed", False))
        
        return available_spots > 0 and working_chargers > 0
    
    def _assign_parking_spot(self, vehicle: Vehicle, vehicle_manager: VehicleManager) -> Optional[int]:
        """Assign an available parking spot to a vehicle."""
        for spot_id in range(self.num_spots):
            if not self.depot_state.spot_occupancy[spot_id]:
                if vehicle_manager.assign_spot(vehicle.vehicle_id, spot_id):
                    return spot_id
        return None
    
    def _assign_charger(self, vehicle: Vehicle) -> Optional[int]:
        """Assign an available charger to a vehicle."""
        for charger_id in range(self.num_chargers):
            status = self.depot_state.charger_status[charger_id]
            if not status.get("connected", False) and not status.get("failed", False):
                return charger_id
        return None
    
    def _is_charger_failed(self, charger_id: Optional[int]) -> bool:
        """Check if a charger has failed."""
        if charger_id is None:
            return False
        status = self.depot_state.charger_status.get(charger_id, {})
        return status.get("failed", False)
    
    def _free_vehicle_resources(self, vehicle: Vehicle, vehicle_manager: VehicleManager):
        """Free up resources used by a departing vehicle."""
        if vehicle.assigned_spot is not None:
            vehicle_manager.free_spot(vehicle.assigned_spot) 
        if vehicle.assigned_charger is not None:
            # Disconnect from charger
            status = self.depot_state.charger_status[vehicle.assigned_charger]
            status["connected"] = False
            status["charging"] = False
    
    def _control_gates(self, vehicle_manager: VehicleManager, current_step: int) -> List[ControlAction]:
        """Control gate operations."""
        actions = []
        
        # Simple gate control: open if vehicles waiting and can admit
        waiting_vehicles = vehicle_manager.get_vehicles_by_state(VehicleState.WAITING)
        approaching_vehicles = vehicle_manager.get_vehicles_by_state(VehicleState.APPROACHING)
        
        should_open_gate = (len(waiting_vehicles) > 0 or len(approaching_vehicles) > 0) and self._can_admit_vehicle()
        
        for gate_id in range(self.num_gates):
            current_state = self.depot_state.gate_states[gate_id]
            if should_open_gate and not current_state:
                actions.append(self._create_action(
                    "depot_controller", "gate_control",
                    f"gate_{gate_id}", "open", current_step
                ))
            elif not should_open_gate and current_state:
                actions.append(self._create_action(
                    "depot_controller", "gate_control", 
                    f"gate_{gate_id}", "close", current_step
                ))
        
        return actions
    
    def _create_action(self, controller: str, action_type: str, target: str, 
                      command: str, current_step: int) -> ControlAction:
        """Create a control action record."""
        return ControlAction(
            action_id=str(uuid.uuid4()),
            step_id=f"step_{current_step}",  # This will be updated by the engine
            controller=controller,
            action_type=action_type,
            target=target,
            command=command,
            success=True
        )