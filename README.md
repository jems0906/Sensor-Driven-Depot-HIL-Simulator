# Depot Sensor / HIL-Style Simulator

A Hardware-in-the-Loop (HIL) style simulator for electric vehicle depot management systems. This project simulates depot operations with sensor monitoring, control logic, and fault detection capabilities.

## Stack
- **Simulation + Control**: Python 3.8+
- **Database**: SQLite 
- **UI**: CLI with optional web dashboard
- **Testing**: Pytest framework

## Requirements

### Functional Requirements

1. **FR-001**: System shall simulate a depot with configurable numbers of gates, chargers, and parking spots.
2. **FR-002**: System shall prevent two vehicles from occupying the same spot simultaneously.
3. **FR-003**: System shall detect charger failures and raise an alert within 5 simulation steps.
4. **FR-004**: System shall log all sensor values, control actions, and faults to a database.
5. **FR-005**: System shall support multiple concurrent vehicles in different operational states.
6. **FR-006**: System shall provide gate control logic based on spot availability and charger status.
7. **FR-007**: System shall simulate realistic sensor noise and occasional false readings.
8. **FR-008**: System shall maintain simulation state consistency across time steps.

### Non-Functional Requirements

1. **NFR-001**: Simulation shall process at least 100 time steps per second.
2. **NFR-002**: System shall maintain 99.9% data integrity for logged events.
3. **NFR-003**: Fault detection latency shall not exceed 5 simulation steps.
4. **NFR-004**: System shall support scenarios up to 1000 time steps.

## Test Scenarios

### Scenario 1: Normal Operation
- **Objective**: Verify basic depot operations without failures
- **Setup**: 2 gates, 5 parking spots, 3 chargers
- **Expected**: All vehicles processed without conflicts or faults
- **Success Criteria**: 
  - Zero overlapping occupancy events
  - All vehicles successfully charge and exit
  - No false alarms

### Scenario 2: Charger Failure During Operation
- **Objective**: Test fault detection and recovery procedures
- **Setup**: Single charger fails at timestep 30 while vehicle is charging
- **Expected**: System detects failure within 5 steps and handles gracefully
- **Success Criteria**:
  - Charger failure detected within 5 simulation steps
  - Vehicle marked as WAITING for alternative charger
  - Alert logged to database

### Scenario 3: Gate Stuck Closed
- **Objective**: Test gate malfunction handling
- **Setup**: Entry gate fails to open despite control signal
- **Expected**: System detects gate malfunction and manages queue
- **Success Criteria**:
  - Gate malfunction detected
  - Queue management activated
  - Alternative routing if available

### Scenario 4: Sensor Noise and False Readings
- **Objective**: Test robustness against sensor interference
- **Setup**: Inject 10% false "spot occupied" readings
- **Expected**: System filters noise and maintains accurate state
- **Success Criteria**:
  - No false spot assignments
  - Actual occupancy correctly tracked
  - Noise events logged but not acted upon

### Scenario 5: High Traffic Load
- **Objective**: Test system under peak operational conditions
- **Setup**: 10 vehicles, 2 gates, 8 spots, 6 chargers
- **Expected**: Efficient queue management and resource allocation
- **Success Criteria**:
  - No deadlock conditions
  - Fair resource allocation
  - Maximum throughput achieved

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Simulation    │    │    Control      │    │    Database     │
│     Engine      │◄──►│     Logic       │◄──►│    Logging      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Sensors      │    │   Actuators     │    │   Reporting     │
│ - Gate Status   │    │ - Gate Control  │    │ - Fault Logs    │
│ - Occupancy     │    │ - Charger Ctrl  │    │ - Metrics       │
│ - Charger State │    │ - Spot Assign   │    │ - Test Results  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run normal operation scenario
python run_sim.py --scenario normal

# Run with charger failure
python run_sim.py --scenario charger_failure

# Run all test scenarios
python -m pytest tests/

# Launch dashboard (optional)
python dashboard.py
```

## File Structure
```
depot-simulator/
├── README.md
├── requirements.txt
├── run_sim.py              # Main CLI entry point
├── src/
│   ├── __init__.py
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── engine.py       # Core simulation loop
│   │   ├── sensors.py      # Sensor implementations
│   │   └── vehicles.py     # Vehicle state management
│   ├── control/
│   │   ├── __init__.py
│   │   ├── depot_controller.py  # Main control logic
│   │   └── fault_detector.py    # Fault detection algorithms
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py       # Database schema
│   │   └── logger.py       # Data logging utilities
│   └── scenarios/
│       ├── __init__.py
│       ├── base.py         # Base scenario class
│       └── test_cases.py   # Predefined test scenarios
├── tests/
│   ├── __init__.py
│   ├── test_simulation.py
│   ├── test_control.py
│   └── test_scenarios.py
└── dashboard/              # Optional web interface
    ├── app.py
    └── templates/
```

## Development Timeline

- **Phase 1**: Requirements & Scenarios ✓
- **Phase 2**: Architecture Design (1-2 hours)
- **Phase 3**: Core Implementation (4-5 hours) 
- **Phase 4**: Test Harness (2-3 hours)
- **Phase 5**: Dashboard (2-3 hours, optional)

## Contributing

This project demonstrates formal verification and validation methods for depot automation systems, including simulation and hardware-in-the-loop testing capabilities.