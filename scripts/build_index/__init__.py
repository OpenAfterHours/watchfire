"""Index builder for watchfire's bundled rulebook parquet.

Run as ``python -m scripts.build_index`` from the repo root, or via the
back-compat shim ``python scripts/build_index.py``. Requires the
``build`` extra: ``uv sync --extra build``.

The output ``src/watchfire/data/index.parquet`` is committed and shipped
in the wheel; the runtime never re-fetches.
"""

from __future__ import annotations
