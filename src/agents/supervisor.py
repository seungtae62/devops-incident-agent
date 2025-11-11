"""LangGraph workflow orchestration for incident response"""

import logging
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
from src.config import Config
from src.agents.log_analyzer import LogAnalyzerAgent
from src.agents.diagnostic import DiagnosticAgent
from src.agents.action import ActionAgent
from src.rag.retriever import DocumentRetriever


# Define the state schema for the workflow
class IncidentState(TypedDict, total=False):
    """State schema for incident response workflow"""
    # Input
    input_log: str
    service_name: str
    severity: str

    # Log Analyzer outputs
    log_analysis: Dict[str, Any]
    extracted_symptoms: List[str]
    error_patterns: List[str]
    search_query: str

    # Retrieval outputs
    similar_incidents: List[Dict[str, Any]]
    relevant_runbooks: List[Dict[str, Any]]

    # Diagnostic outputs
    root_cause: str
    confidence: float
    diagnostic_reasoning: str
    diagnostic_results: Dict[str, Any]

    # Action outputs
    resolution_steps: List[Dict[str, Any]]
    commands: List[str]
    estimated_time: str
    action_plan: Dict[str, Any]

    # Workflow metadata
    current_step: str
    errors: List[str]


class IncidentResponseWorkflow:
    """Orchestrates the incident response workflow using LangGraph"""

    def __init__(self, qdrant_url: str = None):
        """
        Initialize the workflow with all agents
        """
        self.qdrant_url = qdrant_url or Config.QDRANT_URL

        # Initialize agents
        logging.info("Initializing incident response workflow...")
        self.log_analyzer = LogAnalyzerAgent()
        self.diagnostic_agent = DiagnosticAgent()
        self.action_agent = ActionAgent()
        self.retriever = DocumentRetriever(qdrant_url=f"http://{self.qdrant_url}")

        # Build the graph
        self.graph = self._build_graph()
        logging.info("Workflow initialized successfully")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""

        # Create the graph with our state schema
        workflow = StateGraph(IncidentState)

        # Add nodes
        workflow.add_node("log_analyzer", self._log_analyzer_node)
        workflow.add_node("retrieve_context", self._retrieval_node)
        workflow.add_node("diagnostic", self._diagnostic_node)
        workflow.add_node("action", self._action_node)

        # Define the flow
        workflow.set_entry_point("log_analyzer")
        workflow.add_edge("log_analyzer", "retrieve_context")
        workflow.add_edge("retrieve_context", "diagnostic")
        workflow.add_edge("diagnostic", "action")
        workflow.add_edge("action", END)

        # Compile the graph
        return workflow.compile()

    def _log_analyzer_node(self, state: IncidentState) -> Dict[str, Any]:
        """Node for log analysis"""
        logging.info("Step 1: Analyzing logs...")
        try:
            result = self.log_analyzer(state)
            result["current_step"] = "log_analysis_complete"
            return result
        except Exception as e:
            logging.error(f"Error in log analyzer: {e}")
            return {
                "current_step": "log_analysis_failed",
                "errors": state.get("errors", []) + [str(e)]
            }

    def _retrieval_node(self, state: IncidentState) -> Dict[str, Any]:
        """Node for RAG retrieval"""
        logging.info("Step 2: Retrieving similar incidents and runbooks...")
        try:
            # Get search query from log analysis
            search_query = state.get("search_query", state.get("input_log", "")[:500])

            # Search for similar incidents
            similar_incidents = self.retriever.search_incidents(
                query=search_query,
                k=3,
                service_filter=state.get("service_name"),
                severity_filter=state.get("severity")
            )
            logging.info(f"Found {len(similar_incidents)} similar incidents")

            # Search for relevant runbooks
            relevant_runbooks = self.retriever.search_runbooks(
                query=search_query,
                k=3,
                service_filter=state.get("service_name")
            )
            logging.info(f"Found {len(relevant_runbooks)} relevant runbooks")

            return {
                "similar_incidents": similar_incidents,
                "relevant_runbooks": relevant_runbooks,
                "current_step": "retrieval_complete"
            }

        except Exception as e:
            logging.error(f"Error in retrieval: {e}")
            return {
                "similar_incidents": [],
                "relevant_runbooks": [],
                "current_step": "retrieval_failed",
                "errors": state.get("errors", []) + [str(e)]
            }

    def _diagnostic_node(self, state: IncidentState) -> Dict[str, Any]:
        """Node for diagnostic analysis"""
        logging.info("Step 3: Performing diagnostic analysis...")
        try:
            result = self.diagnostic_agent(state)
            result["current_step"] = "diagnostic_complete"
            return result
        except Exception as e:
            logging.error(f"Error in diagnostic: {e}")
            return {
                "root_cause": "Unable to determine",
                "confidence": 0.0,
                "current_step": "diagnostic_failed",
                "errors": state.get("errors", []) + [str(e)]
            }

    def _action_node(self, state: IncidentState) -> Dict[str, Any]:
        """Node for action planning"""
        logging.info("Step 4: Creating action plan...")
        try:
            result = self.action_agent(state)
            result["current_step"] = "action_complete"
            return result
        except Exception as e:
            logging.error(f"Error in action planning: {e}")
            return {
                "resolution_steps": [],
                "commands": [],
                "estimated_time": "Unknown",
                "current_step": "action_failed",
                "errors": state.get("errors", []) + [str(e)]
            }

    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the workflow
        """
        logging.info("Starting incident response workflow")
        logging.info(f"Service: {input_data.get('service_name')}, Severity: {input_data.get('severity')}")

        # Initialize state
        initial_state: IncidentState = {
            "input_log": input_data["input_log"],
            "service_name": input_data["service_name"],
            "severity": input_data.get("severity", "Medium"),
            "current_step": "started",
            "errors": []
        }

        try:
            # Execute the workflow
            final_state = self.graph.invoke(initial_state)

            logging.info("Workflow completed successfully")
            logging.info(f"Root Cause: {final_state.get('root_cause', 'Unknown')}")
            logging.info(f"Confidence: {final_state.get('confidence', 0)}")
            logging.info(f"Estimated Resolution Time: {final_state.get('estimated_time', 'Unknown')}")

            return final_state

        except Exception as e:
            logging.error(f"Workflow execution failed: {e}")
            raise


def create_workflow(qdrant_url: str = None) -> IncidentResponseWorkflow:
    """
    Factory function to create workflow instance
    """
    return IncidentResponseWorkflow(qdrant_url=qdrant_url)
