from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from sklearn.base import BaseEstimator, TransformerMixin

from .exceptions import ModelUnavailableError
from .features import FEATURE_COLUMNS


class MeaningAwareImputer(BaseEstimator, TransformerMixin):
    def fit(self, frame, y=None):
        self.columns_ = list(frame.columns)
        return self

    def transform(self, frame):
        output = frame.copy()
        std_columns = [column for column in self.columns_ if column.endswith("_std")]
        output[std_columns] = output[std_columns].fillna(0.0)
        return output


@lru_cache(maxsize=1)
def load_segmentation_model():
    path = Path(settings.COUGH_SEGMENTATION_MODEL_PATH)
    if not path.is_file():
        raise ModelUnavailableError(f"Cough segmentation model is not installed: {path}")
    from .segmentation import build_model
    model = build_model()
    model.load_weights(str(path))
    return model


@lru_cache(maxsize=1)
def load_infection_classifier():
    path = Path(settings.INFECTION_CLASSIFIER_MODEL_PATH)
    if not path.is_file():
        raise ModelUnavailableError(f"Infection classifier is not installed: {path}")
    import joblib
    artifact = joblib.load(path)
    pipeline = artifact["pipeline"] if isinstance(artifact, dict) else artifact
    columns = artifact.get("feature_columns", FEATURE_COLUMNS) if isinstance(artifact, dict) else FEATURE_COLUMNS
    if list(columns) != FEATURE_COLUMNS:
        raise ModelUnavailableError("Classifier feature schema does not match the 123 inference features.")
    if not hasattr(pipeline, "predict_proba"):
        raise ModelUnavailableError("Classifier does not provide predict_proba().")
    return pipeline


def predict_scores(rows):
    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    return [float(value) for value in np.asarray(load_infection_classifier().predict_proba(frame))[:, 1]]
