#!/usr/bin/env python3
"""
CLI interface for the Incident Triage Agent.
Provides interactive command-line interface for incident triage.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core import IncidentTriageAgent


def print_header():
    """Print CLI header."""
    print("\n" + "=" * 70)
    print("  INCIDENT TRIAGE AGENT")
    print("  Autonomous IT incident classification and response recommendation")
    print("=" * 70 + "\n")


def print_result(result: dict):
    """Pretty print triage result."""
    print("\n" + "=" * 70)
    print("TRIAGE RESULTS")
    print("=" * 70 + "\n")

    # Incident Details
    if result.get("incident_details"):
        details = result["incident_details"]
        print("INCIDENT CLASSIFICATION:")
        print(f"  Severity:       {details.get('severity', 'Unknown').upper()}")
        print(f"  Type:           {details.get('incident_type', 'Unknown').replace('_', ' ').title()}")
        print(f"  Affected:       {', '.join(details.get('affected_systems', ['Unknown']))}")
        print(f"  Confidence:     {details.get('confidence', 'Unknown').title()}")
        print()

    # Mitigation Plan
    if result.get("mitigation_plan"):
        plan = result["mitigation_plan"]
        print("RESPONSE PLAN:")
        print(f"  Target Response Time: {plan.get('target_response_time', 'N/A')}")
        print(f"  Est. Resolution:      {plan.get('estimated_resolution_time', 'N/A')}")
        print()

        print("IMMEDIATE ACTIONS:")
        for i, action in enumerate(plan.get("immediate_actions", []), 1):
            print(f"  {i}. {action}")
        print()

        print("INVESTIGATION STEPS:")
        for i, step in enumerate(plan.get("investigation_steps", []), 1):
            print(f"  {i}. {step}")
        print()

        print("ESCALATION CRITERIA:")
        print(f"  {plan.get('escalation_criteria', 'N/A')}")
        print()

    # Final Response
    if result.get("final_response"):
        print("AGENT SUMMARY:")
        print(f"  {result['final_response']}")
        print()

    # Execution Stats
    print("EXECUTION METRICS:")
    print(f"  Total Iterations:     {result.get('total_iterations', 0)}")
    print(f"  Function Calls:       {len(result.get('execution_log', []))}")
    successful_calls = sum(1 for call in result.get('execution_log', []) if call.get('status') == 'success')
    print(f"  Successful Calls:     {successful_calls}")
    print()
    print("=" * 70 + "\n")


def save_result(result: dict, output_path: str):
    """Save result to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Results saved to: {output_path}")


def interactive_mode():
    """Run agent in interactive mode."""
    print_header()
    print("Interactive Mode - Enter incident descriptions (Ctrl+C or 'quit' to exit)")
    print("-" * 70 + "\n")

    agent = IncidentTriageAgent()

    while True:
        try:
            print("\nEnter incident description (or 'quit' to exit):")
            print("> ", end="", flush=True)

            # Read multi-line input (empty line to submit)
            lines = []
            while True:
                line = input()
                if line.strip().lower() == 'quit':
                    print("\nExiting...")
                    return
                if not line.strip() and lines:
                    break
                if line.strip():
                    lines.append(line)

            if not lines:
                continue

            incident_description = "\n".join(lines)

            print("\nProcessing incident...\n")

            # Triage incident
            result = agent.triage_incident(incident_description)

            # Validate result
            validation = agent.validate_result(result)
            if not validation["valid"]:
                print("\nWARNING: Validation issues detected:")
                for issue in validation["issues"]:
                    print(f"  - {issue}")
                print()

            # Print result
            print_result(result)

            # Ask if user wants to save
            print("Save results to file? (y/N): ", end="", flush=True)
            save_choice = input().strip().lower()
            if save_choice == 'y':
                timestamp = result.get('timestamp', '').replace(':', '-').replace('.', '-')
                filename = f"triage_result_{timestamp}.json"
                save_result(result, filename)

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


def batch_mode(incident_file: str, output_dir: Optional[str] = None):
    """Run agent in batch mode on multiple incidents."""
    print_header()
    print(f"Batch Mode - Processing incidents from: {incident_file}")
    print("-" * 70 + "\n")

    # Read incidents
    with open(incident_file, 'r') as f:
        incidents = json.load(f)

    if not isinstance(incidents, list):
        print("Error: Incident file must contain a JSON array of incident descriptions")
        return

    agent = IncidentTriageAgent()
    results = []

    for i, incident in enumerate(incidents, 1):
        print(f"\nProcessing incident {i}/{len(incidents)}...")

        # Handle different input formats
        if isinstance(incident, dict):
            description = incident.get("description", str(incident))
        else:
            description = str(incident)

        try:
            result = agent.triage_incident(description)
            validation = agent.validate_result(result)

            if not validation["valid"]:
                print(f"WARNING: Validation issues for incident {i}:")
                for issue in validation["issues"]:
                    print(f"  - {issue}")

            results.append({
                "incident_number": i,
                "result": result,
                "validation": validation
            })

            print(f"  ✓ Completed (Severity: {result.get('incident_details', {}).get('severity', 'Unknown')})")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "incident_number": i,
                "error": str(e)
            })

    # Save results
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path(".")

    output_file = output_path / "batch_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nBatch processing complete!")
    print(f"Results saved to: {output_file}")
    print(f"Total incidents: {len(incidents)}")
    print(f"Successful: {sum(1 for r in results if 'error' not in r)}")
    print(f"Errors: {sum(1 for r in results if 'error' in r)}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Incident Triage Agent - Autonomous IT incident classification and response"
    )

    parser.add_argument(
        "--mode",
        choices=["interactive", "batch"],
        default="interactive",
        help="Operation mode (default: interactive)"
    )

    parser.add_argument(
        "--incident",
        type=str,
        help="Single incident description (for quick one-off triage)"
    )

    parser.add_argument(
        "--batch-file",
        type=str,
        help="JSON file containing array of incidents (for batch mode)"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for results (batch mode)"
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="Auto-save results (single incident mode)"
    )

    args = parser.parse_args()

    # Single incident mode
    if args.incident:
        print_header()
        print("Single Incident Mode")
        print("-" * 70 + "\n")

        agent = IncidentTriageAgent()
        result = agent.triage_incident(args.incident)
        validation = agent.validate_result(result)

        if not validation["valid"]:
            print("\nWARNING: Validation issues detected:")
            for issue in validation["issues"]:
                print(f"  - {issue}")
            print()

        print_result(result)

        if args.save:
            timestamp = result.get('timestamp', '').replace(':', '-').replace('.', '-')
            filename = f"triage_result_{timestamp}.json"
            save_result(result, filename)

    # Batch mode
    elif args.mode == "batch":
        if not args.batch_file:
            print("Error: --batch-file required for batch mode")
            parser.print_help()
            return

        batch_mode(args.batch_file, args.output)

    # Interactive mode (default)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
