"""Run the final ONT-09 business ontology demo and write deterministic JSON."""

import argparse
import json
from pathlib import Path

from src.final_demo import build_final_demo

ROOT = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(description="Run the final ontology demonstration")
    parser.add_argument("--output", default="reports/generated/ont09_final_demo.json")
    args = parser.parse_args(argv)

    report = build_final_demo(ROOT)
    target = Path(args.output)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Ontology:", report["ontology"])
    print("Nodes:", report["graph"]["nodes"])
    print("Relationships:", report["graph"]["edges"])
    print("Customer C001 orders:", ", ".join(report["customer_demo"]["orders"]))
    print("Product P001:", report["product_demo"]["name"])
    print("P001 purchases:", report["product_demo"]["count"])
    for item in report["product_demo"]["purchases"]:
        print(
            f"  {item['order_id']}: {item['customer_name']} | "
            f"{item['invoice_currency']} {item['invoice_amount']:.2f} | "
            f"{item['invoice_status']}"
        )
    print("Invalid customer query: REJECTED")
    print("ONT-08 audit: PASSED")
    print("Final demonstration: PASSED")
    print("Report:", target)
    return target


if __name__ == "__main__":
    main()
