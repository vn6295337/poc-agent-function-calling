"""
Core agent logic for incident triage.
Implements the planning and execution loop with function calling.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from agent.llm_client import LLMClient
from functions.handlers import execute_function

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IncidentTriageAgent:
    """
    Autonomous agent for triaging IT incidents using function calling.
    """

    def __init__(self):
        """Initialize the agent."""
        self.llm_client = LLMClient()
        self.functions = self._load_function_schemas()
        self.conversation_history = []
        self.execution_log = []

    def _load_function_schemas(self) -> List[Dict[str, Any]]:
        """Load function schemas from JSON file."""
        schema_path = Path(__file__).parent.parent / "functions" / "schemas.json"

        try:
            with open(schema_path, 'r') as f:
                schema_data = json.load(f)
                return schema_data.get("functions", [])
        except FileNotFoundError:
            logger.error(f"Function schemas not found at {schema_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schemas file: {e}")
            raise

    def triage_incident(self, incident_description: str) -> Dict[str, Any]:
        """
        Triage an incident using the agent loop.

        Args:
            incident_description: Raw incident description from user

        Returns:
            Dictionary with triage results including:
            - incident_details: Extracted structured data
            - mitigation_plan: Recommended actions
            - execution_log: All function calls made
            - final_response: Natural language summary
        """
        logger.info(f"Starting incident triage for: {incident_description[:100]}...")

        # Reset state for new incident
        self.conversation_history = []
        self.execution_log = []

        # Build initial system prompt
        system_prompt = self._build_system_prompt()

        # Initialize conversation
        self.conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please triage this incident:\n\n{incident_description}"}
        ]

        # Execute agent loop
        max_iterations = 10
        iteration = 0
        incident_details = None
        mitigation_plan = None

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agent iteration {iteration}/{max_iterations}")

            # Call LLM with function calling
            response, function_calls = self.llm_client.call_with_functions(
                messages=self.conversation_history,
                functions=self.functions,
                max_iterations=1
            )

            # Check if we got a final response
            if response is not None:
                logger.info("Agent completed triage")
                final_response = response
                break

            # Execute function calls
            if function_calls:
                last_call = function_calls[-1]
                function_name = last_call["function"]
                function_args = last_call["arguments"]

                try:
                    # Execute function
                    logger.info(f"Executing function: {function_name}")
                    result = execute_function(function_name, function_args)

                    # Store results
                    if function_name == "extract_incident_details":
                        incident_details = result
                    elif function_name == "get_standard_mitigation":
                        mitigation_plan = result

                    # Log execution
                    execution_entry = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "iteration": iteration,
                        "function": function_name,
                        "arguments": function_args,
                        "result": result,
                        "status": "success"
                    }
                    self.execution_log.append(execution_entry)

                    logger.info(f"Function {function_name} executed successfully")

                    # Continue conversation with function result
                    tool_use_id = last_call.get("tool_use_id") or last_call.get("tool_call_id")

                    # Update conversation history with assistant tool call and tool response
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_use_id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": json.dumps(function_args)
                            }
                        }]
                    })

                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_use_id,
                        "content": json.dumps(result)
                    })

                    # Don't call continue_with_function_result, just continue the loop
                    # The next iteration will use the updated conversation_history
                    continue

                    # Check if we got final response after function execution
                    if response is not None:
                        logger.info("Agent completed triage after function execution")
                        final_response = response
                        break

                    # If more function calls requested, continue loop
                    if new_calls:
                        function_calls.extend(new_calls)

                except Exception as e:
                    logger.error(f"Error executing function {function_name}: {e}")
                    execution_entry = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "iteration": iteration,
                        "function": function_name,
                        "arguments": function_args,
                        "error": str(e),
                        "status": "error"
                    }
                    self.execution_log.append(execution_entry)

                    # Add error to conversation and retry
                    self.conversation_history.append({
                        "role": "user",
                        "content": f"Function execution failed with error: {str(e)}. Please try a different approach."
                    })
            else:
                # No function calls and no response - error state
                logger.error("LLM returned neither response nor function calls")
                final_response = "Error: Agent failed to process incident"
                break

        else:
            # Max iterations reached
            logger.warning("Max iterations reached")
            final_response = "Incident analysis incomplete. Maximum iterations reached."

        # Compile final result
        result = {
            "incident_description": incident_description,
            "incident_details": incident_details,
            "mitigation_plan": mitigation_plan,
            "final_response": final_response,
            "execution_log": self.execution_log,
            "total_iterations": iteration,
            "timestamp": datetime.utcnow().isoformat()
        }

        return result

    def _build_system_prompt(self) -> str:
        """Build system prompt for the agent."""
        return """You are an expert IT incident triage agent. Your role is to:

1. Analyze incident descriptions to extract structured information (severity, type, affected systems)
2. Recommend standard mitigation procedures based on the incident classification
3. Provide clear, actionable guidance for incident responders

You have access to the following functions:
- extract_incident_details: Analyzes incident text to determine severity, type, and affected systems
- get_standard_mitigation: Retrieves standard mitigation playbooks based on incident classification

Process for triaging an incident:
1. First, call extract_incident_details to analyze the incident description
2. Then, use the extracted information to call get_standard_mitigation
3. Finally, provide a clear summary with:
   - Incident classification (severity and type)
   - Affected systems
   - Immediate actions to take
   - Investigation steps
   - Escalation criteria

Be concise, precise, and focus on actionable information."""

    def validate_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the triage result for completeness and correctness.

        Args:
            result: Triage result from triage_incident()

        Returns:
            Validation report with any issues found
        """
        validation = {
            "valid": True,
            "issues": [],
            "warnings": []
        }

        # Check required fields
        if not result.get("incident_details"):
            validation["valid"] = False
            validation["issues"].append("Missing incident_details")

        if not result.get("mitigation_plan"):
            validation["valid"] = False
            validation["issues"].append("Missing mitigation_plan")

        if not result.get("final_response"):
            validation["valid"] = False
            validation["issues"].append("Missing final_response")

        # Validate incident_details structure
        if result.get("incident_details"):
            details = result["incident_details"]
            required_fields = ["severity", "incident_type", "affected_systems"]

            for field in required_fields:
                if field not in details:
                    validation["valid"] = False
                    validation["issues"].append(f"incident_details missing field: {field}")

            # Check severity is valid
            valid_severities = ["critical", "high", "medium", "low"]
            if details.get("severity") not in valid_severities:
                validation["warnings"].append(f"Unusual severity: {details.get('severity')}")

        # Validate mitigation_plan structure
        if result.get("mitigation_plan"):
            plan = result["mitigation_plan"]
            required_fields = ["immediate_actions", "investigation_steps", "escalation_criteria"]

            for field in required_fields:
                if field not in plan:
                    validation["valid"] = False
                    validation["issues"].append(f"mitigation_plan missing field: {field}")

        # Check execution log
        if not result.get("execution_log"):
            validation["warnings"].append("Empty execution log")
        elif len(result["execution_log"]) > 5:
            validation["warnings"].append(f"Many function calls: {len(result['execution_log'])}")

        validation["timestamp"] = datetime.utcnow().isoformat()
        return validation
