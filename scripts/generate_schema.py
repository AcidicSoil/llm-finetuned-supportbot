from __future__ import annotations

import json
import os

from src.models import DataRecord


def main() -> None:
    schema = DataRecord.model_json_schema()
    os.makedirs("schema", exist_ok=True)
    out_path = os.path.join("schema", "data_schema.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"Wrote schema to {out_path}")


if __name__ == "__main__":
    main()
