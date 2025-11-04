import streamlit as st
from src.config import Config
# from agents.graph import create_workflow

st.set_page_config(
    page_title="DevOps Incident Response Agent",
    layout="wide"
)

def main():
    st.title("DevOps Incident Response Agent")

    with st.sidebar:
        st.header("Settings")
        service_name = st.selectbox(
            "Select Service",
            ["API Gateway", "Database", "etc"]
        )
        severity = st.radio(
            "Severity",
            ["Critical", "High", "Medium", "Low"]
        )

    log_input = st.text_area(
        "Log input",
        height=200,
        placeholder="Please copy and paste your logs..."
    )

    if st.button("Start Analysis", type="primary"):
        if log_input:
            with st.spinner("Analyzing"):
                pass
                # workflow = create_workflow()
                # result = workflow.invoke({
                #     "input_log": log_input,
                #     "service_name": service_name
                # })

                # display_results(result)
        else:
            st.warning("Please paste your logs!")

if __name__ == "__main__":
    Config.validate()
    main()
