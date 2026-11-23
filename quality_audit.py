"""Run the ONT-08 quality audit and save a deterministic JSON report."""

import argparse
import json
from pathlib import Path

from src.quality_audit import audit_project


ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Audit synthetic business graph end to end")
    parser.add_argument("--output", default="reports/generated/ont08_audit.json")
    args = parser.parse_args()

    report = audit_project(ROOT)
    target = Path(args.output)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Ontology: {report['ontology']}")
    print(f"Entities: {report['node_count']}")
    print(f"Relationships: {report['edge_count']}")
    print(f"Bidirectional relationships checked: {report['bidirectional_edges_checked']}")
    print(f"Product queries checked: {report['product_queries_checked']}")
    print(f"Invalid queries rejected: {report['invalid_queries_rejected']}")
    print("Quality audit: PASSED")
    print(f"Report: {target}")


if __name__ == "__main__":
    main()
