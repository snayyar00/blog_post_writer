"""
Generate a cost report for API usage.
"""

from src.utils.cost_tracker import generate_cost_report, save_cost_report

def main():
    """Generate and save a cost report."""
    # Generate the report
    report = generate_cost_report()
    
    # Print the report to console
    print("\n" + report + "\n")
    
    # Save the report to a file
    report_path = save_cost_report("api_cost_report.md")
    print(f"Cost report saved to: {report_path}")

if __name__ == "__main__":
    main()