from pathlib import Path

import joblib
import lightgbm as lgb
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from cough_analysis.features import FEATURE_COLUMNS
from cough_analysis.modeling import MeaningAwareImputer


class Command(BaseCommand):
    help = "Train and export the default binary LightGBM infection classifier."

    def add_arguments(self, parser):
        parser.add_argument("data_path", type=Path)
        parser.add_argument("--output", type=Path, default=Path("models/infection_classifier.joblib"))

    def handle(self, *args, **options):
        data_path, output = options["data_path"], options["output"]
        if not data_path.is_file():
            raise CommandError(f"Dataset not found: {data_path}")
        frame = pd.read_csv(data_path)
        missing = [column for column in [*FEATURE_COLUMNS, "isInfectious"] if column not in frame]
        if missing:
            raise CommandError(f"Required columns are missing: {missing}")
        labels = frame["isInfectious"].map({"Negative": 0, "Positive": 1})
        valid = labels.notna()
        if labels.loc[valid].nunique() != 2:
            raise CommandError("Both Positive and Negative training rows are required.")
        x = frame.loc[valid, FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
        pipeline = Pipeline([
            ("meaning_imputer", MeaningAwareImputer()),
            ("fallback_imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", lgb.LGBMClassifier(random_state=42)),
        ])
        pipeline.fit(x, labels.loc[valid].astype(int))
        output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": pipeline, "feature_columns": FEATURE_COLUMNS,
                     "label": "isInfectious", "positive_class": "Positive",
                     "aggregation": "arithmetic_mean"}, output)
        self.stdout.write(self.style.SUCCESS(f"Saved classifier trained on {len(x)} rows to {output}"))
