#!/usr/bin/env bash
# Build an isolated wheel and verify the installed CLI and packaged active assets.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

uv build --wheel --out-dir "$work/dist" "$root"
uv venv --no-project --python "${PYTHON:-python3}" "$work/venv"
uv pip install --python "$work/venv/bin/python" "$work"/dist/*.whl
"$work/venv/bin/storycraft" --help
"$work/venv/bin/python" - <<'PY'
from storycraft.prompt_template import get_template_loader
from storycraft.series_model import OpenAIStoryModel

loader = get_template_loader()

schema = loader.load_schema_object(
    "generate",
    "scene_continuity",
)
assert isinstance(schema, dict)
assert schema.get("type") == "object"
assert isinstance(schema.get("properties"), dict)
assert schema["properties"]

prompt = OpenAIStoryModel._render(
    "generate",
    "scene_continuity",
    context={},
)
assert isinstance(prompt, str)
assert prompt.strip()

print("packaged active templates and schemas: OK")
PY
