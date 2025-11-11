"""Action Agent - Generates resolution plans using runbook context"""

import json
import logging
from typing import Dict, Any, List
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.config import Config
from src.agents.prompts.action import (
    ACTION_SYSTEM_PROMPT,
    ACTION_USER_PROMPT
)


class ActionAgent:
    """Agent that creates actionable resolution plans based on diagnosis"""

    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=Config.AI_ENDPOINT,
            api_key=Config.AI_API_KEY,
            api_version="2024-02-01",
            deployment_name=Config.AI_DEPLOY_GPT4O,  # Using GPT-4o for detailed instructions
            temperature=0.3  # Slightly higher for creative adaptation of runbooks
        )
        logging.info("ActionAgent initialized with GPT-4o")

    def create_action_plan(
        self,
        diagnostic_results: Dict[str, Any],
        relevant_runbooks: List[Dict[str, Any]],
        service_name: str,
        severity: str
    ) -> Dict[str, Any]:

        logging.info(f"Creating action plan for {service_name}")
        logging.debug(f"Using {len(relevant_runbooks)} runbooks as reference")

        # Format runbooks for the prompt
        runbooks_text = self._format_runbooks(relevant_runbooks)

        # Format diagnostic results
        diagnostic_text = json.dumps(diagnostic_results, indent=2)

        # Create user prompt
        user_prompt = ACTION_USER_PROMPT.format(
            diagnostic_results=diagnostic_text,
            service_name=service_name,
            severity=severity,
            relevant_runbooks=runbooks_text
        )

        # Create messages
        messages = [
            SystemMessage(content=ACTION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        try:
            # Invoke LLM
            response = self.llm.invoke(messages)

            # Parse JSON response
            result = self._parse_response(response.content)

            logging.info(f"Action plan created: {result.get('resolution_summary', 'N/A')}")
            logging.debug(f"Estimated time: {result.get('estimated_time', 'Unknown')}")

            return result

        except Exception as e:
            logging.error(f"Error during action plan creation: {e}")
            raise

    def _format_runbooks(self, runbooks: List[Dict[str, Any]]) -> str:
        """Format runbooks for the prompt"""
        if not runbooks:
            return "No relevant runbooks found in the database. Please create a custom resolution plan based on best practices."

        formatted = []
        for i, runbook in enumerate(runbooks, 1):
            content = runbook.get("content", "")
            metadata = runbook.get("metadata", {})
            score = runbook.get("score", 0)

            runbook_text = f"""
### Runbook #{i} (Relevance Score: {score:.2f})
**Runbook ID:** {metadata.get('runbook_id', 'N/A')}
**Service:** {metadata.get('service', 'N/A')}
**Category:** {metadata.get('category', 'N/A')}
**Estimated Time:** {metadata.get('estimated_time', 'N/A')}
**Severity:** {metadata.get('severity', 'N/A')}

**Content:**
{content}
"""
            formatted.append(runbook_text)

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
                "resolution_summary": "Unable to create structured action plan due to parsing error",
                "estimated_time": "Unknown",
                "priority": "High",
                "immediate_actions": [],
                "root_cause_resolution": [],
                "validation_steps": [],
                "monitoring": {
                    "duration": "30 minutes",
                    "metrics_to_watch": [],
                    "alert_conditions": "Any increase in error rate"
                },
                "rollback_procedure": [],
                "prevention_recommendations": [],
                "runbooks_used": [],
                "raw_response": response_content,  # Include raw response
                "parse_error": str(e)
            }

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node function
        """
        result = self.create_action_plan(
            diagnostic_results=state.get("diagnostic_results", {}),
            relevant_runbooks=state.get("relevant_runbooks", []),
            service_name=state["service_name"],
            severity=state["severity"]
        )

        return {
            "resolution_steps": result.get("immediate_actions", []) + result.get("root_cause_resolution", []),
            "commands": self._extract_commands(result),
            "estimated_time": result.get("estimated_time", "Unknown"),
            "action_plan": result  # Store full plan
        }

    def _extract_commands(self, action_plan: Dict[str, Any]) -> List[str]:
        """Extract all commands from the action plan"""
        commands = []

        # Extract from immediate actions
        for action in action_plan.get("immediate_actions", []):
            commands.extend(action.get("commands", []))

        # Extract from root cause resolution
        for action in action_plan.get("root_cause_resolution", []):
            commands.extend(action.get("commands", []))

        return commands
