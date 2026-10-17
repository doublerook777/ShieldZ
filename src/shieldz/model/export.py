"""Model export utilities: JSON, ONNX, and metadata generation.

Saves model.json (XGBoost format), model.onnx (validated via onnx.checker),
and model_meta.json containing feature order, thresholds, and training metadata (Gate M2).
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from shieldz.config import model_dir, thresholds_file
from shieldz.contracts import FEATURE_ORDER
from shieldz.model.engine import XGBoostEngine


def get_git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return "unknown"


def export_model_artifacts(
    engine: XGBoostEngine,
    output_dir: Path | str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Export model.json, model_meta.json, and model.onnx."""
    out_dir = Path(output_dir) if output_dir is not None else model_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, Path] = {}

    # 1. Save XGBoost native JSON
    json_path = out_dir / "model.json"
    engine.booster.save_model(str(json_path))
    artifacts["json"] = json_path

    # 2. Save metadata
    thresh_path = thresholds_file()
    thresholds = {}
    if thresh_path.exists():
        try:
            thresholds = json.loads(thresh_path.read_text())
        except Exception:
            pass

    meta = {
        "name": engine.name,
        "version": engine.version,
        "feature_order": list(FEATURE_ORDER),
        "thresholds": thresholds,
        "git_sha": get_git_sha(),
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    if extra_meta:
        meta.update(extra_meta)

    meta_path = out_dir / "model_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    artifacts["meta"] = meta_path

    # 3. Export to ONNX if converter available
    onnx_path = out_dir / "model.onnx"
    try:
        import onnx
        from onnxmltools import convert_xgboost
        from onnxmltools.convert.common.data_types import FloatTensorType

        initial_types = [("input", FloatTensorType([None, len(FEATURE_ORDER)]))]
        orig_names = getattr(engine.booster, "feature_names", None)
        try:
            engine.booster.feature_names = [f"f{i}" for i in range(len(FEATURE_ORDER))]
            onnx_model = convert_xgboost(engine.booster, initial_types=initial_types)
            onnx.checker.check_model(onnx_model)
            onnx.save_model(onnx_model, str(onnx_path))
            print(f"ONNX model saved and verified: {onnx_path}")
            artifacts["onnx"] = onnx_path
        finally:
            if orig_names is not None:
                engine.booster.feature_names = orig_names
    except Exception as exc:
        print(f"ONNX export skipped: {exc}")

    return artifacts
