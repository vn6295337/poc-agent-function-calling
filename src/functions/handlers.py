"""
Function handlers for incident triage agent.
Implements the actual logic for each function defined in schemas.json
"""

import re
from typing import Dict, List, Any
from datetime import datetime


def extract_incident_details(incident_description: str) -> Dict[str, Any]:
    """
    Extracts structured information from an incident description.

    Uses rule-based analysis and keyword matching to determine:
    - Severity level (critical, high, medium, low)
    - Incident type (outage, breach, degradation, etc.)
    - Affected systems (extracted from description)
    - Key details and timestamps

    Args:
        incident_description: Raw incident text

    Returns:
        Dictionary with extracted structured data
    """
    description = incident_description.lower()

    # Severity detection based on keywords
    severity = "medium"  # default
    if any(word in description for word in ["down", "outage", "critical", "complete failure", "all users affected"]):
        severity = "critical"
    elif any(word in description for word in ["breach", "security", "unauthorized", "compromised", "exploit"]):
        severity = "critical"
    elif any(word in description for word in ["slow", "degraded", "intermittent", "some users"]):
        severity = "high"
    elif any(word in description for word in ["minor", "cosmetic", "low impact"]):
        severity = "low"

    # Incident type classification
    incident_type = "unknown"
    if any(word in description for word in ["down", "outage", "unavailable", "not responding"]):
        incident_type = "service_outage"
    elif any(word in description for word in ["breach", "security", "unauthorized", "hack", "compromised"]):
        incident_type = "security_breach"
    elif any(word in description for word in ["slow", "degraded", "latency", "timeout", "performance"]):
        incident_type = "performance_degradation"
    elif any(word in description for word in ["data loss", "deleted", "missing data", "corrupted"]):
        incident_type = "data_loss"
    elif any(word in description for word in ["network", "connectivity", "dns", "routing"]):
        incident_type = "network_issue"
    elif any(word in description for word in ["config", "misconfiguration", "settings", "deployment failed"]):
        incident_type = "configuration_error"
    elif any(word in description for word in ["capacity", "disk full", "memory", "cpu", "resource"]):
        incident_type = "capacity_issue"

    # Extract affected systems (simple pattern matching)
    affected_systems = []

    # Common system patterns
    system_patterns = [
        r"(\w+)\s+(?:service|server|database|api|application)",
        r"(?:service|server|db|api)[\s-](\w+)",
    ]

    for pattern in system_patterns:
        matches = re.findall(pattern, description)
        affected_systems.extend(matches)

    # Remove duplicates and clean
    affected_systems = list(set([s.strip() for s in affected_systems if s.strip()]))

    # If no systems detected, mark as unknown
    if not affected_systems:
        affected_systems = ["system_unknown"]

    result = {
        "severity": severity,
        "incident_type": incident_type,
        "affected_systems": affected_systems,
        "description_summary": incident_description[:200],  # First 200 chars
        "analyzed_at": datetime.utcnow().isoformat(),
        "confidence": "high" if incident_type != "unknown" else "low"
    }

    return result


def get_standard_mitigation(
    incident_type: str,
    severity: str,
    affected_systems: List[str] = None
) -> Dict[str, Any]:
    """
    Returns standard mitigation steps based on incident type and severity.

    Provides:
    - Immediate actions (first 5-15 minutes)
    - Investigation steps
    - Escalation criteria
    - Estimated resolution time

    Args:
        incident_type: Type of incident (from enum)
        severity: Severity level (critical, high, medium, low)
        affected_systems: Optional list of affected systems

    Returns:
        Dictionary with mitigation plan
    """
    affected_systems = affected_systems or []

    # Define mitigation playbooks
    playbooks = {
        "service_outage": {
            "immediate_actions": [
                "Verify service status via monitoring dashboards",
                "Check recent deployments or configuration changes",
                "Attempt service restart if safe to do so",
                "Activate incident response team"
            ],
            "investigation_steps": [
                "Review application logs for errors",
                "Check infrastructure health (CPU, memory, disk)",
                "Verify database connectivity and performance",
                "Check for upstream/downstream service dependencies"
            ],
            "escalation_criteria": "If service not restored within 15 minutes or impact >1000 users"
        },
        "security_breach": {
            "immediate_actions": [
                "Isolate affected systems from network",
                "Preserve logs and evidence",
                "Notify security team and management immediately",
                "Begin incident response protocol"
            ],
            "investigation_steps": [
                "Identify attack vector and entry point",
                "Assess scope of compromise",
                "Review access logs and authentication events",
                "Check for data exfiltration or unauthorized access"
            ],
            "escalation_criteria": "Immediate escalation to CISO and legal team"
        },
        "performance_degradation": {
            "immediate_actions": [
                "Monitor current resource utilization",
                "Check for unusual traffic patterns or load",
                "Review recent code or configuration changes",
                "Consider scaling resources if needed"
            ],
            "investigation_steps": [
                "Analyze application performance metrics",
                "Review slow query logs and database performance",
                "Check for memory leaks or resource exhaustion",
                "Verify CDN and caching layer health"
            ],
            "escalation_criteria": "If degradation persists >30 minutes or worsens"
        },
        "data_loss": {
            "immediate_actions": [
                "Stop all write operations if possible",
                "Identify scope and timeframe of data loss",
                "Locate most recent backup",
                "Notify data owners and stakeholders"
            ],
            "investigation_steps": [
                "Determine root cause of data loss",
                "Verify backup integrity and completeness",
                "Plan restoration procedure",
                "Document affected records or transactions"
            ],
            "escalation_criteria": "Immediate escalation if customer data affected"
        },
        "network_issue": {
            "immediate_actions": [
                "Verify network connectivity to critical systems",
                "Check DNS resolution and routing tables",
                "Review firewall and security group rules",
                "Contact network operations team"
            ],
            "investigation_steps": [
                "Trace network path and identify failure point",
                "Check for ISP or cloud provider incidents",
                "Review recent network configuration changes",
                "Verify BGP routes and peering status"
            ],
            "escalation_criteria": "If network unavailable >10 minutes"
        },
        "configuration_error": {
            "immediate_actions": [
                "Identify recent configuration changes",
                "Rollback to last known good configuration",
                "Verify rollback restored functionality",
                "Document the problematic change"
            ],
            "investigation_steps": [
                "Compare current vs previous configuration",
                "Test configuration in staging environment",
                "Review change approval and validation",
                "Update configuration management procedures"
            ],
            "escalation_criteria": "If rollback unsuccessful or impact unclear"
        },
        "capacity_issue": {
            "immediate_actions": [
                "Free up resources (clear cache, remove temp files)",
                "Scale up infrastructure if auto-scaling enabled",
                "Identify largest resource consumers",
                "Implement rate limiting if needed"
            ],
            "investigation_steps": [
                "Analyze resource growth trends",
                "Identify capacity planning gaps",
                "Review resource allocation and quotas",
                "Plan for capacity expansion"
            ],
            "escalation_criteria": "If resources reach 90%+ utilization"
        },
        "unknown": {
            "immediate_actions": [
                "Gather detailed incident information",
                "Engage incident response team",
                "Monitor system health metrics",
                "Document all symptoms and observations"
            ],
            "investigation_steps": [
                "Review all recent changes (code, config, infra)",
                "Check monitoring dashboards for anomalies",
                "Correlate with external incidents or outages",
                "Consult subject matter experts"
            ],
            "escalation_criteria": "Escalate within 15 minutes for classification"
        }
    }

    # Get playbook or use unknown as fallback
    playbook = playbooks.get(incident_type, playbooks["unknown"])

    # Adjust response time based on severity
    response_times = {
        "critical": "5 minutes",
        "high": "15 minutes",
        "medium": "1 hour",
        "low": "4 hours"
    }

    resolution_estimates = {
        "critical": "15 minutes - 2 hours",
        "high": "1 - 4 hours",
        "medium": "4 - 24 hours",
        "low": "1 - 3 days"
    }

    result = {
        "incident_type": incident_type,
        "severity": severity,
        "affected_systems": affected_systems,
        "immediate_actions": playbook["immediate_actions"],
        "investigation_steps": playbook["investigation_steps"],
        "escalation_criteria": playbook["escalation_criteria"],
        "target_response_time": response_times.get(severity, "1 hour"),
        "estimated_resolution_time": resolution_estimates.get(severity, "Unknown"),
        "generated_at": datetime.utcnow().isoformat()
    }

    return result


# Function registry for dynamic dispatch
FUNCTION_REGISTRY = {
    "extract_incident_details": extract_incident_details,
    "get_standard_mitigation": get_standard_mitigation
}


def execute_function(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a function by name with the given arguments.

    Args:
        function_name: Name of function to execute
        arguments: Dictionary of function arguments

    Returns:
        Function execution result

    Raises:
        ValueError: If function name not found in registry
    """
    if function_name not in FUNCTION_REGISTRY:
        raise ValueError(f"Unknown function: {function_name}")

    func = FUNCTION_REGISTRY[function_name]
    return func(**arguments)
