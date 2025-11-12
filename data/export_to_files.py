"""Export Qdrant collections to JSON files for file-based RAG"""

import json
from qdrant_client import QdrantClient
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

QDRANT_URL = "localhost"
QDRANT_PORT = 6333
OUTPUT_DIR = Path(__file__).parent / "vectors"


def export_collection(client: QdrantClient, collection_name: str, output_file: Path) -> int:
    """
    Export a Qdrant collection to JSON file
    """
    logging.info(f"Exporting {collection_name}...")

    points = []
    offset = None

    # Scroll through all points
    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )

        batch_points, next_offset = result

        if not batch_points:
            break

        for point in batch_points:
            # Extract data
            point_data = {
                "id": str(point.id),
                "text": point.payload.get("text", ""),
                "embedding": point.vector.tolist() if hasattr(point.vector, 'tolist') else point.vector,
                "metadata": point.payload
            }
            points.append(point_data)

        if next_offset is None:
            break

        offset = next_offset

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(points, f, indent=2, ensure_ascii=False)

    logging.info(f"Exported {len(points)} points to {output_file}")
    return len(points)


def main():
    """Main export function"""
    logging.info("=" * 80)
    logging.info("EXPORTING QDRANT DATA TO JSON FILES")
    logging.info("=" * 80)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    logging.info(f"Output directory: {OUTPUT_DIR}")

    try:
        # Connect to Qdrant
        logging.info(f"Connecting to Qdrant at {QDRANT_URL}:{QDRANT_PORT}...")
        client = QdrantClient(host=QDRANT_URL, port=QDRANT_PORT)

        # Test connection
        collections = client.get_collections()
        logging.info(f"Connected! Found {len(collections.collections)} collections")

        # Export collections
        incidents_count = export_collection(
            client,
            "devops_incidents",
            OUTPUT_DIR / "incidents.json"
        )

        runbooks_count = export_collection(
            client,
            "devops_runbooks",
            OUTPUT_DIR / "runbooks.json"
        )

        # Summary
        logging.info("=" * 80)
        logging.info("EXPORT COMPLETED SUCCESSFULLY")
        logging.info("=" * 80)
        logging.info(f"Incidents: {incidents_count} points → {OUTPUT_DIR / 'incidents.json'}")
        logging.info(f"Runbooks:  {runbooks_count} points → {OUTPUT_DIR / 'runbooks.json'}")
        logging.info("You can now use file-based RAG without Qdrant server!")
        logging.info("=" * 80)

    except Exception as e:
        logging.error(f"Export failed: {e}")
        logging.error("Make sure:")
        logging.error("  1. Qdrant is running: docker-compose up -d")
        logging.error("  2. Data is loaded: python data/data_script.py")
        logging.error("  3. Collections exist: devops_incidents, devops_runbooks")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
