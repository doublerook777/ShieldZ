"""Model training, evaluation, inference engines, and reason codes."""

from shieldz.model.data import get_peak_rss_mb, load_paysim, time_based_split
from shieldz.model.engine import XGBoostEngine
from shieldz.model.evaluate import evaluate_model
from shieldz.model.export import export_model_artifacts
from shieldz.model.reasons import extract_reasons_from_contribs
from shieldz.model.train import run_training_pipeline, train_xgboost

__all__ = [
    "XGBoostEngine",
    "evaluate_model",
    "export_model_artifacts",
    "extract_reasons_from_contribs",
    "get_peak_rss_mb",
    "load_paysim",
    "run_training_pipeline",
    "time_based_split",
    "train_xgboost",
]
