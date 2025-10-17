#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import statistics

def get_metric(result_json_path: str, metric_key: str = "max_cov") -> float:
    """
    Extract a specific metric from a result.json file.
    This is a standalone function that can be easily modified to change metrics.
    
    Args:
        result_json_path: Path to the result.json file
        metric_key: The key to extract from the JSON (default: "max_cov")
    
    Returns:
        The metric value as a float, or None if not found
    """
    try:
        with open(result_json_path, 'r') as f:
            data = json.load(f)
            # Look for the metric in the fuzz_data section
            if "fuzz_data" in data and metric_key in data["fuzz_data"]:
                return float(data["fuzz_data"][metric_key])
            else:
                return None
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"Error reading {result_json_path}: {e}")
        return None

def get_metric_label() -> str:
    """
    Returns the label for the current metric being used.
    Modify this when changing the metric calculation.
    """
    return "Average Max Coverage"

def collect_metrics(base_dir: str) -> Dict[str, Dict[str, List[float]]]:
    """
    Collect metrics from all result.json files organized by condition and test.
    
    Returns:
        Dictionary: {condition: {test_name: [metric_values]}}
    """
    metrics = defaultdict(lambda: defaultdict(list))
    
    conditions = ["initial-only", "pure-fuzz", "with-feedback", "eqq-initial"]
    test_pattern = "crs-workdir/{condition}/HarnessRunner/aixcc/jvm/imaging/{test}/fuzz/*/result.json"
    
    for condition in conditions:
        # Find all test directories
        imaging_dir = Path(f"crs-workdir/{condition}/HarnessRunner/aixcc/jvm/imaging")
        if not imaging_dir.exists():
            continue
            
        for test_dir in imaging_dir.iterdir():
            if test_dir.is_dir():
                test_name = test_dir.name
                
                # Find all result.json files for this test
                result_files = list(test_dir.glob("fuzz/*/result.json"))
                
                for result_file in result_files:
                    metric_value = get_metric(str(result_file))
                    if metric_value is not None:
                        metrics[condition][test_name].append(metric_value)
    
    return metrics

def calculate_averages(metrics: Dict[str, Dict[str, List[float]]]) -> Dict[str, Dict[str, float]]:
    """
    Calculate average metrics for each condition and test.
    
    Returns:
        Dictionary: {condition: {test_name: average_metric}}
    """
    averages = defaultdict(dict)
    
    for condition, tests in metrics.items():
        for test_name, values in tests.items():
            if values:
                averages[condition][test_name] = statistics.mean(values)
    
    return averages

def print_comparison_table(metrics: Dict[str, Dict[str, List[float]]]):
    """
    Print a formatted comparison table of metrics across conditions.
    """
    averages = calculate_averages(metrics)
    
    # Get all unique test names
    all_tests = set()
    for condition_tests in averages.values():
        all_tests.update(condition_tests.keys())
    all_tests = sorted(all_tests)
    
    if not all_tests:
        print("No test data found!")
        return
    
    # Print header
    print("\n" + "="*100)
    print(f"Comparison Table - Metric: {get_metric_label()}")
    print("="*100)
    
    # Column headers
    header = f"{'Test Name':<25} {'Initial-Only':<20} {'Pure-Fuzz':<20} {'With-Feedback':<20} {'Eqq-Initial':<20}"
    print(header)
    print("-"*100)
    
    # Print data for each test
    for test_name in all_tests:
        row_data = [test_name[:24]]  # Truncate test name if too long
        
        for condition in ["initial-only", "pure-fuzz", "with-feedback", "eqq-initial"]:
            if condition in averages and test_name in averages[condition]:
                avg_value = averages[condition][test_name]
                # Also show count of runs
                count = len(metrics[condition][test_name]) if condition in metrics else 0
                row_data.append(f"{avg_value:.1f} (n={count})")
            else:
                row_data.append("N/A")
        
        print(f"{row_data[0]:<25} {row_data[1]:<20} {row_data[2]:<20} {row_data[3]:<20} {row_data[4]:<20}")
    
    print("-"*100)
    
    # Print overall averages
    print("\nOverall Statistics:")
    print("-"*100)
    
    for condition in ["initial-only", "pure-fuzz", "with-feedback", "eqq-initial"]:
        if condition in averages:
            all_values = []
            for test_name in averages[condition]:
                all_values.extend(metrics[condition][test_name])
            
            if all_values:
                overall_avg = statistics.mean(all_values)
                overall_std = statistics.stdev(all_values) if len(all_values) > 1 else 0
                overall_min = min(all_values)
                overall_max = max(all_values)
                
                print(f"{condition.title():<15}: "
                      f"Avg={overall_avg:.1f}, "
                      f"Std={overall_std:.1f}, "
                      f"Min={overall_min:.1f}, "
                      f"Max={overall_max:.1f}, "
                      f"Total runs={len(all_values)}")
    
    print("="*100)

def main():
    """Main function to run the analysis."""
    print("Analyzing coverage metrics...")
    
    # Collect all metrics
    metrics = collect_metrics(".")
    
    # Print comparison table
    print_comparison_table(metrics)
    
    # Print summary of data availability
    print("\nData Summary:")
    for condition in ["initial-only", "pure-fuzz", "with-feedback", "eqq-initial"]:
        if condition in metrics:
            test_count = len(metrics[condition])
            total_runs = sum(len(values) for values in metrics[condition].values())
            print(f"  {condition}: {test_count} tests, {total_runs} total runs")
        else:
            print(f"  {condition}: No data found")

if __name__ == "__main__":
    main()
