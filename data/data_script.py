"""
Script to push sample incidents and runbooks data to Qdrant DB
"""

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.rag.vector_store import VectorStoreManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def load_json_data(file_path: Path):
    with open(file_path, 'r') as f:
        return json.load(f)


def push_data():
    """Push sample data to Qdrant vector database"""

    # Incident Data
    logging.debug("Proccessing incident data")
    incident_file = Config.DATA_DIR / "incidents/sample_incidents.json"

    if not incident_file.exists():
        logging.error(f"Incident file not found: {incident_file}")
        return False

    incident_data = load_json_data(incident_file)
    logging.info(f"Loaded {len(incident_data)} incidents from {incident_file.name}")

    incident_store = VectorStoreManager(
        store_type="incidents",
        qdrant_url=Config.QDRANT_URL
    )

    # Check if collection exists
    if incident_store.collection_exists():
        logging.info("Incident collection already exists")
        response = input("Delete and recreate? (y/n): ")
        if response.lower() == 'y':
            incident_store.delete_collection()

    logging.info("Adding documents to Qdrant (generating embeddings)...")
    incident_store.add_documents(documents=incident_data)

    # Verify
    info = incident_store.get_collection_info()
    logging.debug(f"{info['points_count']} incidents added to collection '{info['name']}'")

    # Runbook Data
    logging.debug("Processing runbook data")
    runbook_file = Config.DATA_DIR / "runbooks/sample_runbooks.json"

    if not runbook_file.exists():
        logging.error(f"Runbook file not found: {runbook_file}")
        return False

    runbook_data = load_json_data(runbook_file)
    logging.debug(f"Loaded {len(runbook_data)} runbooks from {runbook_file.name}")

    runbook_store = VectorStoreManager(
        store_type="runbooks",
        qdrant_url=Config.QDRANT_URL
    )

    # Check if collection exists
    if runbook_store.collection_exists():
        logging.info("Runbook collection already exists")
        response = input("Delete and recreate? (y/n): ")
        if response.lower() == 'y':
            runbook_store.delete_collection()

    logging.info("Adding documents to Qdrant (generating embeddings)...")
    runbook_store.add_documents(documents=runbook_data)

    # Verify
    info = runbook_store.get_collection_info()
    logging.debug(f"{info['points_count']} runbooks added to collection '{info['name']}'")

    return True


def main():
    logging.info(f"Qdrant URL: {Config.QDRANT_URL}")
    logging.info(f"Data Directory: {Config.DATA_DIR}")

    # Validate configuration
    try:
        Config.validate()
        logging.info("✓ Environment configuration validated")
    except Exception as e:
        logging.error(f"✗ Environment configuration error: {e}")
        return

    # Push data to Qdrant
    try:
        success = push_data()
        if not success:
            logging.error("Data push failed. Check errors above.")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error during data push: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
