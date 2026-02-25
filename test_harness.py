"""
Test harness script to run all scenarios and generate a test report.
"""

import subprocess
import sys
import os
import sqlite3
from datetime import datetime


def run_scenario(scenario_name):
    """Run a single scenario and capture results."""
    print(f"Running scenario: {scenario_name}")
    
    try:
        # Run the simulation
        result = subprocess.run([
            sys.executable, "run_sim.py", "--scenario", scenario_name, "--verbose"
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        success = "PASSED" in result.stdout
        return {
            "scenario": scenario_name,
            "success": success,
            "output": result.stdout,
            "errors": result.stderr
        }
    except Exception as e:
        return {
            "scenario": scenario_name, 
            "success": False,
            "output": "",
            "errors": str(e)
        }


def run_unit_tests():
    """Run unit tests."""
    print("Running unit tests...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/", "-v"
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "errors": str(e)
        }


def generate_report(scenario_results, unit_test_results):
    """Generate a test report."""
    
    report = f"""
# Depot HIL Simulator Test Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Test Summary
"""
    
    # Scenario results
    total_scenarios = len(scenario_results)
    passed_scenarios = sum(1 for r in scenario_results if r["success"])
    
    report += f"""
### Scenario Tests: {passed_scenarios}/{total_scenarios} PASSED

| Scenario | Result |
|----------|--------|
"""
    
    for result in scenario_results:
        status = "PASS" if result["success"] else "FAIL"
        report += f"| {result['scenario']} | {status} |\n"
    
    # Unit test results  
    unit_status = "PASS" if unit_test_results["success"] else "FAIL"
    report += f"""
### Unit Tests: {unit_status}

## Detailed Results

### Unit Test Output
```
{unit_test_results['output']}
```

### Scenario Details
"""
    
    for result in scenario_results:
        report += f"""
#### {result['scenario']}
Status: {'PASSED' if result['success'] else 'FAILED'}

```
{result['output']}
```
"""
        if result['errors']:
            report += f"""
Errors:
```
{result['errors']}
```
"""
    
    return report


def main():
    """Main test harness execution."""
    print("=== Depot HIL Simulator Test Harness ===\n")
    
    # Test scenarios to run
    scenarios = [
        "normal",
        "charger_failure", 
        "gate_stuck",
        "sensor_noise",
        "high_traffic"
    ]
    
    # Run all scenarios
    scenario_results = []
    for scenario in scenarios:
        result = run_scenario(scenario)
        scenario_results.append(result)
        print(f"  {scenario}: {'PASSED' if result['success'] else 'FAILED'}")
    
    # Run unit tests
    unit_test_results = run_unit_tests()
    print(f"  Unit Tests: {'PASSED' if unit_test_results['success'] else 'FAILED'}")
    
    # Generate report
    report = generate_report(scenario_results, unit_test_results)
    
    # Write report to file
    with open("test_report.md", "w", encoding='utf-8') as f:
        f.write(report)
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Scenarios: {sum(1 for r in scenario_results if r['success'])}/{len(scenario_results)} passed")
    print(f"Unit Tests: {'PASSED' if unit_test_results['success'] else 'FAILED'}")
    print(f"Report saved to: test_report.md")
    
    # Exit with appropriate code
    all_passed = (all(r["success"] for r in scenario_results) and 
                  unit_test_results["success"])
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()