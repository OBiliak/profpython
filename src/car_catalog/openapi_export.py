"""Export the OpenAPI schema of the REST API to a file: python -m car_catalog.openapi_export [path].

The same JSON as GET /openapi.json, but without a running server; docs/openapi.json is kept in Git.
"""

import json
import sys
from pathlib import Path

from car_catalog.api import app

DEFAULT_PATH = Path("docs") / "openapi.json"


def openapi_text() -> str:
    """OpenAPI schema as formatted JSON text (Ukrainian letters are not escaped)."""
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the schema; return the exit code."""
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else DEFAULT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(openapi_text(), encoding="utf-8")
    schema = app.openapi()
    print(f"OpenAPI {schema['openapi']}: {len(schema['paths'])} paths → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
