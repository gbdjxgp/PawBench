# -*- coding: utf-8 -*-
"""pawbench.utils — pure-function helpers with no internal dependencies."""

from pawbench.utils.anomalies import detect_anomalies
from pawbench.utils.model_id_utils import normalize_model_id, slugify_model

__all__ = [
    "detect_anomalies",
    "normalize_model_id",
    "slugify_model",
]
