"""Log Analyzer Agent - Extracts structured information from raw logs"""

import json
import logging
from typing import Dict, Any
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.config import Config
from src.agents.prompts.log_analyzer import (
    LOG_ANALYZER_SYSTEM_PROMPT,
    LOG_ANALYZER_USER_PROMPT
)


class LogAnalyzerAgent:
    """Agent that analyzes raw logs and extracts structured information"""

    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=Config.AI_ENDPOINT,
            api_key=Config.AI_API_KEY,
            api_version="2024-02-01",
            deployment_name=Config.AI_DEPLOY_GPT4O_MINI,  # Using mini for cost efficiency
            temperature=0.1  # Low temperature for consistent extraction
        )
        logging.info("LogAnalyzerAgent initialized with GPT-4o-mini")

    def analyze(self, input_log: str, service_name: str, severity: str) -> Dict[str, Any]:
        """
        Analyze raw logs and extract structured information
        """
        logging.info(f"Analyzing logs for service: {service_name}, severity: {severity}")

        # Format the user prompt with actual values
        user_prompt = LOG_ANALYZER_USER_PROMPT.format(
            service_name=service_name,
            severity=severity,
            input_log=input_log
        )

        # Create messages
        messages = [
            SystemMessage(content=LOG_ANALYZER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        try:
            # Invoke LLM
            response = self.llm.invoke(messages)

            # Parse JSON response
            result = self._parse_response(response.content)

            logging.info("Log analysis completed successfully")
            logging.debug(f"Analysis summary: {result.get('summary', 'N/A')}")

            return result

        except Exception as e:
            logging.error(f"Error during log analysis: {e}")
            raise

    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        """Parse LLM response and extract JSON"""
        try:
            # Try to find JSON in the response
            # LLM might wrap JSON in markdown code blocks
            if "```json" in response_content:
                # Extract JSON from code block
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                json_str = response_content[start:end].strip()
            elif "```" in response_content:
                # Generic code block
                start = response_content.find("```") + 3
                end = response_content.find("```", start)
                json_str = response_content[start:end].strip()
            else:
                # Assume entire response is JSON
                json_str = response_content.strip()

            # Parse JSON
            result = json.loads(json_str)
            return result

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}")
            logging.error(f"Response content: {response_content}")
            # Return a fallback structure
            return {
                "summary": "Failed to parse log analysis",
                "error_patterns": [],
                "symptoms": ["Unable to extract structured information"],
                "affected_components": [service_name],
                "timestamps": [],
                "severity_assessment": severity,
                "key_metrics": {},
                "search_query": input_log[:200],  # Use first 200 chars as fallback
                "parse_error": str(e)
            }

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node function
        """
        result = self.analyze(
            input_log=state["input_log"],
            service_name=state["service_name"],
            severity=state["severity"]
        )

        return {
            "log_analysis": result,
            "extracted_symptoms": result.get("symptoms", []),
            "error_patterns": result.get("error_patterns", []),
            "search_query": result.get("search_query", "")
        }
