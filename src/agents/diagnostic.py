"""Diagnostic Agent - Performs root cause analysis using RAG context"""

import json
import logging
from typing import Dict, Any, List
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.config import Config
from src.agents.prompts.diagnostic import (
    DIAGNOSTIC_SYSTEM_PROMPT,
    DIAGNOSTIC_USER_PROMPT
)


class DiagnosticAgent:
    """Agent that performs root cause analysis using similar incident context"""

    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=Config.AI_ENDPOINT,
            api_key=Config.AI_API_KEY,
            api_version="2024-02-01",
            deployment_name=Config.AI_DEPLOY_GPT4O,  # Using GPT-4o for complex reasoning
            temperature=0.2  # Low temperature for consistent reasoning
        )
        logging.info("DiagnosticAgent initialized with GPT-4o")

    def diagnose(
        self,
        log_analysis: Dict[str, Any],
        similar_incidents: List[Dict[str, Any]],
        service_name: str,
        severity: str
    ) -> Dict[str, Any]:
        """
        Perform root cause analysis
        """
        logging.info(f"Performing diagnostic analysis for {service_name}")
        logging.debug(f"Using {len(similar_incidents)} similar incidents as context")

        # Format similar incidents for the prompt
        incidents_text = self._format_incidents(similar_incidents)

        # Format log analysis
        log_analysis_text = json.dumps(log_analysis, indent=2)

        # Create user prompt
        user_prompt = DIAGNOSTIC_USER_PROMPT.format(
            log_analysis=log_analysis_text,
            service_name=service_name,
            severity=severity,
            similar_incidents=incidents_text
        )

        # Create messages
        messages = [
            SystemMessage(content=DIAGNOSTIC_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        try:
            # Invoke LLM
            response = self.llm.invoke(messages)

            # Parse JSON response
            result = self._parse_response(response.content)

            logging.info(f"Diagnostic completed: {result.get('root_cause', 'Unknown')}")
            logging.debug(f"Confidence: {result.get('confidence', 0)}")

            return result

        except Exception as e:
            logging.error(f"Error during diagnostic analysis: {e}")
            raise

    def _format_incidents(self, incidents: List[Dict[str, Any]]) -> str:
        """Format similar incidents for the prompt"""
        if not incidents:
            return "No similar incidents found in the database."

        formatted = []
        for i, incident in enumerate(incidents, 1):
            content = incident.get("content", "")
            metadata = incident.get("metadata", {})
            score = incident.get("score", 0)

            incident_text = f"""
### Similar Incident #{i} (Similarity Score: {score:.2f})
**Incident ID:** {metadata.get('incident_id', 'N/A')}
**Service:** {metadata.get('service', 'N/A')}
**Severity:** {metadata.get('severity', 'N/A')}
**Date:** {metadata.get('date', 'N/A')}
**Root Cause:** {metadata.get('root_cause', 'N/A')}
**Resolution Time:** {metadata.get('resolution_time', 'N/A')}

**Details:**
{content}
"""
            formatted.append(incident_text)

        return "\n".join(formatted)

    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM response and extract JSON"""
        try:
            # Try to find JSON in the response
            if "```json" in response_content:
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                json_str = response_content[start:end].strip()
            elif "```" in response_content:
                start = response_content.find("```") + 3
                end = response_content.find("```", start)
                json_str = response_content[start:end].strip()
            else:
                json_str = response_content.strip()

            result = json.loads(json_str)
            return result

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}")
            logging.error(f"Response content: {response_content}")
            # Return a fallback structure
            return {
                "root_cause": "Unable to determine root cause due to parsing error",
                "confidence": 0.0,
                "reasoning": response_content,  # Include raw response
                "supporting_evidence": [],
                "similar_incident_matches": [],
                "alternative_causes": [],
                "next_diagnostic_steps": [],
                "parse_error": str(e)
            }

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node function
        """
        result = self.diagnose(
            log_analysis=state["log_analysis"],
            similar_incidents=state.get("similar_incidents", []),
            service_name=state["service_name"],
            severity=state["severity"]
        )

        return {
            "root_cause": result.get("root_cause", ""),
            "confidence": result.get("confidence", 0.0),
            "diagnostic_reasoning": result.get("reasoning", ""),
            "diagnostic_results": result  # Store full results for action agent
        }
