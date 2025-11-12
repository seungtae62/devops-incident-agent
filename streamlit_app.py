import streamlit as st
import json
from src.config import Config
from src.agents.supervisor import create_workflow
from src.rag.retriever import DocumentRetriever

st.set_page_config(
    page_title="DevOps Incident Response Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stAlert {
        margin-top: 1rem;
    }
    .incident-section {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def display_results(result):
    """Display workflow results in a structured format"""

    # Header with root cause
    st.header("Analysis Results")

    # Root Cause Section
    st.subheader("Root Cause Analysis")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Root Cause:** {result.get('root_cause', 'Unknown')}")
    with col2:
        confidence = result.get('confidence', 0)
        confidence_color = "green" if confidence > 0.7 else "orange" if confidence > 0.4 else "red"
        st.markdown(f"**Confidence:** :{confidence_color}[{confidence:.0%}]")

    # Diagnostic Reasoning
    with st.expander("Diagnostic Reasoning", expanded=True):
        diagnostic_results = result.get('diagnostic_results', {})
        st.write(diagnostic_results.get('reasoning', 'No reasoning provided'))

        # Supporting Evidence
        if diagnostic_results.get('supporting_evidence'):
            st.markdown("**Supporting Evidence:**")
            for evidence in diagnostic_results['supporting_evidence']:
                st.markdown(f"- {evidence}")

    # Similar Incidents
    similar_incidents = result.get('similar_incidents', [])
    if similar_incidents:
        with st.expander(f"Similar Historical Incidents ({len(similar_incidents)} found)"):
            for i, incident in enumerate(similar_incidents, 1):
                metadata = incident.get('metadata', {})
                score = incident.get('score', 0)

                st.markdown(f"**Incident #{i}** - Similarity: {score:.0%}")
                st.markdown(f"- **ID:** {metadata.get('incident_id', 'N/A')}")
                st.markdown(f"- **Service:** {metadata.get('service', 'N/A')}")
                st.markdown(f"- **Root Cause:** {metadata.get('root_cause', 'N/A')}")
                st.markdown(f"- **Resolution Time:** {metadata.get('resolution_time', 'N/A')}")
                st.divider()

    # Resolution Plan
    st.subheader("Resolution Plan")
    action_plan = result.get('action_plan', {})

    # Summary
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Summary:** {action_plan.get('resolution_summary', 'No summary available')}")
    with col2:
        st.info(f"**Estimated Time:** {action_plan.get('estimated_time', 'Unknown')}")

    # Immediate Actions
    immediate_actions = action_plan.get('immediate_actions', [])
    if immediate_actions:
        with st.expander("Immediate Actions", expanded=True):
            for action in immediate_actions:
                st.markdown(f"**Step {action.get('step')}:** {action.get('action')}")

                if action.get('safety_note'):
                    st.warning(f"{action['safety_note']}")

                if action.get('commands'):
                    st.code('\n'.join(action['commands']), language='bash')

                if action.get('expected_output'):
                    st.markdown(f"*Expected output:* {action['expected_output']}")

                st.divider()

    # Root Cause Resolution
    root_resolution = action_plan.get('root_cause_resolution', [])
    if root_resolution:
        with st.expander("Root Cause Resolution Steps"):
            for action in root_resolution:
                st.markdown(f"**Step {action.get('step')}:** {action.get('action')}")

                if action.get('why'):
                    st.caption(f"Why: {action['why']}")

                if action.get('commands'):
                    st.code('\n'.join(action['commands']), language='bash')

                if action.get('expected_output'):
                    st.markdown(f"*Expected output:* {action['expected_output']}")

                st.divider()

    # Validation Steps
    validation_steps = action_plan.get('validation_steps', [])
    if validation_steps:
        with st.expander("Validation & Verification"):
            for step in validation_steps:
                st.markdown(f"**Check:** {step.get('check')}")
                if step.get('command'):
                    st.code(step['command'], language='bash')
                st.markdown(f"*Success criteria:* {step.get('success_criteria')}")
                st.divider()

    # Monitoring
    monitoring = action_plan.get('monitoring', {})
    if monitoring:
        with st.expander("Post-Resolution Monitoring"):
            st.markdown(f"**Duration:** {monitoring.get('duration', 'N/A')}")

            if monitoring.get('metrics_to_watch'):
                st.markdown("**Metrics to watch:**")
                for metric in monitoring['metrics_to_watch']:
                    st.markdown(f"- {metric}")

            if monitoring.get('alert_conditions'):
                st.warning(f"**Alert if:** {monitoring['alert_conditions']}")

    # Prevention Recommendations
    prevention = action_plan.get('prevention_recommendations', [])
    if prevention:
        with st.expander("Prevention & Long-term Improvements"):
            for rec in prevention:
                st.markdown(f"- {rec}")

    # Log Analysis Details
    with st.expander("Log Analysis Details"):
        log_analysis = result.get('log_analysis', {})
        st.json(log_analysis)


def main():
    st.title("DevOps Incident Response Agent")
    st.markdown("AI-powered incident analysis and resolution assistant")

    # Sidebar settings
    with st.sidebar:
        st.header("Settings")

        # Service selection - using common services from sample data
        service_name = st.selectbox(
            "Select Service",
            [
                "API Gateway",
                "Database",
                "Cache",
                "Kubernetes",
                "Load Balancer",
                "Network",
                "Security",
                "Message Queue",
                "Storage"
            ]
        )

        # Severity selection
        severity = st.radio(
            "Severity Level",
            ["Critical", "High", "Medium", "Low"],
            index=0
        )

        st.divider()

        # System status
        st.subheader("System Status")
        try:
            Config.validate()
            st.success("✓ Configuration valid")

            # Show Qdrant status
            retriever = DocumentRetriever(qdrant_url=f"http://{Config.QDRANT_URL}")
            status = retriever.get_status()

            incidents_count = status.get('incidents', {}).get('points_count', 0)
            runbooks_count = status.get('runbooks', {}).get('points_count', 0)

            st.info(f"Incidents: {incidents_count}")
            st.info(f"Runbooks: {runbooks_count}")

        except Exception as e:
            st.error(f"System error: {str(e)}")

    # Main content area
    st.subheader("Log Input")

    # Example logs button
    col1, col2 = st.columns([4, 1])
    with col1:
        log_input = st.text_area(
            "Paste your logs here",
            height=250,
            placeholder="Paste error logs, stack traces, or system logs here...",
            help="Provide raw logs from your system. The agent will analyze them to identify the issue."
        )

    with col2:
        st.markdown("**Quick Examples:**")
        if st.button("DB Timeout", use_container_width=True):
            log_input = """
[2024-01-15 10:23:45] ERROR: Connection timeout after 30s
[2024-01-15 10:23:45] ERROR: Failed to connect to database: postgresql://db:5432
[2024-01-15 10:23:46] ERROR: Connection pool exhausted (50/50 connections in use)
[2024-01-15 10:23:47] ERROR: 504 Gateway Timeout
[2024-01-15 10:23:48] ERROR: Query timeout: SELECT * FROM users WHERE email = 'test@example.com'
"""
            st.rerun()

        if st.button("OOM Error", use_container_width=True):
            log_input = """
[2024-02-12 14:30:22] ERROR: Container 'app-worker-xyz' was OOMKilled
[2024-02-12 14:30:22] ERROR: java.lang.OutOfMemoryError: Java heap space
[2024-02-12 14:30:23] WARN: Pod 'app-worker-xyz' restarting (attempt 5/10)
[2024-02-12 14:30:25] ERROR: Memory usage: 512Mi/512Mi (100%)
"""
            st.rerun()

    # Analysis button
    if st.button("Start Analysis", type="primary", use_container_width=True):
        if not log_input or not log_input.strip():
            st.warning("Please paste your logs first!")
        else:
            with st.spinner("Analyzing incident... This may take 30-60 seconds."):
                try:
                    # Create workflow
                    workflow = create_workflow()

                    # Execute analysis
                    result = workflow.invoke({
                        "input_log": log_input,
                        "service_name": service_name,
                        "severity": severity
                    })

                    # Check for errors
                    if result.get('errors'):
                        st.error("Some errors occurred during analysis:")
                        for error in result['errors']:
                            st.error(f"- {error}")

                    # Display results
                    display_results(result)

                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.exception(e)


if __name__ == "__main__":
    try:
        Config.validate()
        main()
    except Exception as e:
        st.error(f"Configuration error: {str(e)}")
        st.info("Please check your .env file and ensure all required settings are configured.")
