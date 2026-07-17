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
from storycraft.series_model import OpenAIStoryModel
from storycraft.prompt_template import get_template_loader

assert "source_scene_id" in get_template_loader().load_schema_text("generate", "continuity")
assert "# closure の生成" in OpenAIStoryModel._render("generate", "closure", context={})
print("packaged active templates and schemas: OK")
PY
