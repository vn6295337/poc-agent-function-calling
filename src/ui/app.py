"""
Streamlit UI for Incident Triage Agent.
Provides web-based interface for incident triage.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

import streamlit as st

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core import IncidentTriageAgent


def init_session_state():
    """Initialize Streamlit session state."""
    if "agent" not in st.session_state:
        st.session_state.agent = IncidentTriageAgent()
    if "history" not in st.session_state:
        st.session_state.history = []


def render_triage_result(result: dict):
    """Render triage result in Streamlit."""

    # Incident Classification
    if result.get("incident_details"):
        details = result["incident_details"]

        st.subheader("📊 Incident Classification")

        col1, col2, col3 = st.columns(3)

        with col1:
            severity = details.get("severity", "Unknown").upper()
            severity_color = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢"
            }.get(severity, "⚪")

            st.metric("Severity", f"{severity_color} {severity}")

        with col2:
            incident_type = details.get("incident_type", "Unknown").replace("_", " ").title()
            st.metric("Type", incident_type)

        with col3:
            confidence = details.get("confidence", "Unknown").title()
            st.metric("Confidence", confidence)

        st.write("**Affected Systems:**")
        systems = details.get("affected_systems", ["Unknown"])
        for system in systems:
            st.write(f"- {system}")

        st.divider()

    # Mitigation Plan
    if result.get("mitigation_plan"):
        plan = result["mitigation_plan"]

        st.subheader("🚨 Response Plan")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Target Response Time", plan.get("target_response_time", "N/A"))
        with col2:
            st.metric("Est. Resolution Time", plan.get("estimated_resolution_time", "N/A"))

        st.write("**Immediate Actions:**")
        for i, action in enumerate(plan.get("immediate_actions", []), 1):
            st.write(f"{i}. {action}")

        with st.expander("📋 Investigation Steps"):
            for i, step in enumerate(plan.get("investigation_steps", []), 1):
                st.write(f"{i}. {step}")

        with st.expander("⚠️ Escalation Criteria"):
            st.write(plan.get("escalation_criteria", "N/A"))

        st.divider()

    # Agent Summary
    if result.get("final_response"):
        st.subheader("🤖 Agent Summary")
        st.info(result["final_response"])
        st.divider()

    # Execution Metrics
    with st.expander("📈 Execution Metrics"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Iterations", result.get("total_iterations", 0))

        with col2:
            total_calls = len(result.get("execution_log", []))
            st.metric("Function Calls", total_calls)

        with col3:
            successful = sum(1 for call in result.get("execution_log", [])
                           if call.get("status") == "success")
            st.metric("Successful Calls", successful)

        # Execution log details
        if result.get("execution_log"):
            st.write("**Execution Log:**")
            for entry in result["execution_log"]:
                status_icon = "✅" if entry.get("status") == "success" else "❌"
                st.write(f"{status_icon} `{entry.get('function')}` - {entry.get('status')}")

    # Raw JSON
    with st.expander("📄 Raw JSON Result"):
        st.json(result)


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Incident Triage Agent",
        page_icon="🚨",
        layout="wide"
    )

    init_session_state()

    # Header
    st.title("🚨 Incident Triage Agent")
    st.markdown("Autonomous IT incident classification and response recommendation using LLM function calling")

    st.divider()

    # Sidebar
    with st.sidebar:
        st.header("📖 About")
        st.write("""
        This agent uses LLM function calling to:
        1. Extract incident details (severity, type, systems)
        2. Recommend standard mitigation procedures
        3. Provide actionable guidance

        Built with OpenAI/Anthropic function calling APIs.
        """)

        st.divider()

        st.header("📝 Sample Incidents")
        samples = [
            "Production API down - database timeout",
            "Unauthorized admin access detected",
            "Slow page loads - high CPU usage",
            "Disk space at 95% on DB server",
            "Network packet loss between servers"
        ]

        for sample in samples:
            if st.button(sample, key=sample):
                st.session_state.sample_incident = sample

        st.divider()

        # History
        st.header("📚 History")
        if st.session_state.history:
            st.write(f"Total triaged: {len(st.session_state.history)}")
            if st.button("Clear History"):
                st.session_state.history = []
                st.rerun()
        else:
            st.write("No incidents triaged yet")

    # Main content
    tab1, tab2 = st.tabs(["🔍 Triage Incident", "📊 Batch Processing"])

    with tab1:
        st.header("Enter Incident Description")

        # Check if sample was selected
        initial_value = st.session_state.get("sample_incident", "")
        if initial_value:
            del st.session_state.sample_incident

        incident_description = st.text_area(
            "Describe the incident:",
            height=150,
            placeholder="Example: Production database is down. Users cannot log in. Error: connection timeout.",
            value=initial_value
        )

        col1, col2 = st.columns([1, 5])
        with col1:
            triage_button = st.button("🚀 Triage Incident", type="primary", use_container_width=True)

        if triage_button and incident_description:
            with st.spinner("🔄 Analyzing incident..."):
                try:
                    # Triage incident
                    result = st.session_state.agent.triage_incident(incident_description)

                    # Validate
                    validation = st.session_state.agent.validate_result(result)

                    if not validation["valid"]:
                        st.warning("⚠️ Validation issues detected:")
                        for issue in validation["issues"]:
                            st.write(f"- {issue}")

                    # Add to history
                    st.session_state.history.append({
                        "timestamp": datetime.now().isoformat(),
                        "description": incident_description[:100] + "...",
                        "severity": result.get("incident_details", {}).get("severity", "Unknown"),
                        "result": result
                    })

                    # Display result
                    st.success("✅ Incident triage completed!")
                    st.divider()

                    render_triage_result(result)

                    # Download button
                    result_json = json.dumps(result, indent=2)
                    st.download_button(
                        label="📥 Download Result (JSON)",
                        data=result_json,
                        file_name=f"triage_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())

        elif triage_button:
            st.warning("⚠️ Please enter an incident description")

    with tab2:
        st.header("Batch Incident Processing")

        uploaded_file = st.file_uploader(
            "Upload JSON file with incidents",
            type=["json"],
            help="Upload a JSON file containing an array of incident descriptions"
        )

        if uploaded_file:
            try:
                incidents = json.load(uploaded_file)

                if not isinstance(incidents, list):
                    st.error("❌ File must contain a JSON array of incidents")
                else:
                    st.info(f"📄 Loaded {len(incidents)} incidents")

                    if st.button("🚀 Process All Incidents", type="primary"):
                        results = []
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        for i, incident in enumerate(incidents):
                            status_text.text(f"Processing incident {i+1}/{len(incidents)}...")

                            # Extract description
                            if isinstance(incident, dict):
                                description = incident.get("description", str(incident))
                            else:
                                description = str(incident)

                            try:
                                result = st.session_state.agent.triage_incident(description)
                                validation = st.session_state.agent.validate_result(result)

                                results.append({
                                    "incident_number": i + 1,
                                    "result": result,
                                    "validation": validation
                                })

                            except Exception as e:
                                results.append({
                                    "incident_number": i + 1,
                                    "error": str(e)
                                })

                            progress_bar.progress((i + 1) / len(incidents))

                        status_text.text("✅ Batch processing complete!")

                        # Summary
                        st.success(f"Processed {len(incidents)} incidents")
                        successful = sum(1 for r in results if "error" not in r)
                        st.metric("Successful", f"{successful}/{len(incidents)}")

                        # Download results
                        results_json = json.dumps(results, indent=2)
                        st.download_button(
                            label="📥 Download All Results (JSON)",
                            data=results_json,
                            file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )

                        # Display results
                        for result_entry in results:
                            if "error" not in result_entry:
                                with st.expander(f"Incident #{result_entry['incident_number']}"):
                                    render_triage_result(result_entry["result"])
                            else:
                                with st.expander(f"Incident #{result_entry['incident_number']} - ERROR"):
                                    st.error(result_entry["error"])

            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file")


if __name__ == "__main__":
    main()
