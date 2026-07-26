#!/usr/bin/env bash
# Build an isolated wheel and verify the installed CLI and packaged active assets.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

python -m pip wheel --no-deps --wheel-dir "$work/dist" "$root"
python -m venv "$work/venv"
"$work/venv/bin/pip" install "$work"/dist/*.whl
"$work/venv/bin/storycraft" --help
"$work/venv/bin/python" - <<'PY'
from storycraft.prompt_template import get_template_loader
from storycraft.series_model import OpenAIStoryModel

loader = get_template_loader()

schema = loader.load_schema_object(
    "generate",
    "scene_continuity_v1",
)
assert isinstance(schema, dict)
assert schema.get("type") == "object"
assert isinstance(schema.get("properties"), dict)
assert schema["properties"]

prompt = OpenAIStoryModel._render(
    "generate",
    "scene_continuity_v1",
    context={},
)
assert isinstance(prompt, str)
assert prompt.strip()

print("packaged active templates and schemas: OK")
PY
