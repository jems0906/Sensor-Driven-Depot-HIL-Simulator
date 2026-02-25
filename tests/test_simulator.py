"""
Basic tests for the Depot HIL Simulator.
"""

import sys
import os
import tempfile
import unittest

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.simulation.engine import SimulationEngine, SimulationConfig
from src.database.models import DatabaseManager
from src.simulation.vehicles import Vehicle, VehicleManager, VehicleState


class TestDepotSimulator(unittest.TestCase):
    
    def setUp(self):
        """Set up test database and simulation."""
        self.db_file = tempfile.mktemp(suffix='.db')
        self.db_manager = DatabaseManager(self.db_file)
        self.db_manager.connect()
        self.db_manager.init_schema()
        
        self.config = SimulationConfig(
            num_gates=2,
            num_spots=5,
            num_chargers=3,
            max_steps=10,
            vehicle_arrival_rate=0.5
        )
    
    def tearDown(self):
        """Clean up test database."""
        self.db_manager.close()
        if os.path.exists(self.db_file):
            os.unlink(self.db_file)
    
    def test_simulation_runs(self):
        """Test that basic simulation runs without errors."""
        engine = SimulationEngine(self.config, self.db_manager)
        results = engine.run_complete_simulation("test_normal")
        
        self.assertIsNotNone(results["run_id"])
        self.assertGreater(results["total_steps"], 0)
        self.assertIsInstance(results["step_results"], list)
    
    def test_vehicle_management(self):
        """Test vehicle management functionality."""
        vm = VehicleManager()
        
        # Create and add vehicle
        vehicle = Vehicle.create_new(0)
        vm.add_vehicle(vehicle)
        
        self.assertEqual(len(vm.vehicles), 1)
        
        # Test spot assignment
        success = vm.assign_spot(vehicle.vehicle_id, 0)
        self.assertTrue(success)
        self.assertEqual(vehicle.assigned_spot, 0)
        
        # Test conflict detection (no conflicts initially)
        conflicts = vm.detect_occupancy_conflicts()
        self.assertEqual(len(conflicts), 0)
    
    def test_no_occupancy_conflicts(self):
        """Test that normal operation produces no occupancy conflicts."""
        engine = SimulationEngine(self.config, self.db_manager)
        results = engine.run_complete_simulation("test_no_conflicts")
        
        # Check database for occupancy conflicts
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM fault_events 
            WHERE fault_type = 'occupancy_conflict'
        """)
        conflict_count = cursor.fetchone()[0]
        
        self.assertEqual(conflict_count, 0, "Found occupancy conflicts in normal operation")
    
    def test_charger_failure_detection(self):
        """Test that charger failures are detected within required time."""
        # Configure scenario with charger failure
        config = SimulationConfig(
            num_gates=2,
            num_spots=5, 
            num_chargers=3,
            max_steps=50,
            vehicle_arrival_rate=0.5,
            charger_failure_step=10
        )
        
        engine = SimulationEngine(config, self.db_manager)
        results = engine.run_complete_simulation("test_charger_failure")
        
        # Check that charger failure was detected within 5 steps
        cursor = self.db_manager.connection.cursor()
        cursor.execute("""
            SELECT detected_at FROM fault_events 
            WHERE fault_type = 'charger_failure'
            ORDER BY detected_at LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            detection_step = result[0]
            detection_delay = detection_step - 10  # failure injected at step 10
            self.assertLessEqual(detection_delay, 5, 
                               f"Charger failure detected too late (delay: {detection_delay} steps)")


if __name__ == '__main__':
    unittest.main()