# Cough check backend

The Django API detects every cough in an uploaded recording, extracts the 123
non-active acoustic features, predicts an infectious-disease score for each
cough with binary LightGBM, and returns the arithmetic mean.

M4A and other codecs not supported by libsndfile are decoded through the
system `ffmpeg` command. Production images must include ffmpeg.

## Model setup

The cough detector defaults to the existing `coughs共有用/nicholas/slideCNN_fold1.keras`.
Train the production classifier from the approved labelled CSV:

```bash
uv run python manage.py train_infection_classifier /path/to/elderly.csv \
  --output models/infection_classifier.joblib
```

The CSV must contain `isInfectious` (`Positive`/`Negative`) and all 123 feature
columns. Model paths can be overridden with `COUGH_SEGMENTATION_MODEL_PATH` and
`INFECTION_CLASSIFIER_MODEL_PATH`.

## API

```bash
curl -X POST http://localhost:8000/api/cough-check/analyze/ -F 'audio=@sample.wav'
```

```json
{
  "cough_count": 2,
  "average_positive_score": 0.5,
  "coughs": [
    {"index": 1, "start_sec": 0.1, "end_sec": 0.8, "positive_score": 0.2},
    {"index": 2, "start_sec": 1.5, "end_sec": 2.2, "positive_score": 0.8}
  ]
}
```

With no detected cough, `average_positive_score` is `null`. This score is an
uncalibrated model output, not a clinical diagnosis probability.
