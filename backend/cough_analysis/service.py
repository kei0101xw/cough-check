import tempfile
from pathlib import Path

import numpy as np

from .exceptions import InvalidAudioError
from .features import SAMPLE_RATE, extract_features, load_audio
from .modeling import load_segmentation_model, predict_scores
from .segmentation import detect_segments


def analyze_audio_path(path):
    try:
        audio = load_audio(path)
    except Exception as exc:
        raise InvalidAudioError("The uploaded file could not be decoded as audio.") from exc
    segments = detect_segments(audio, load_segmentation_model())
    if not segments:
        return {"cough_count": 0, "average_positive_score": None, "coughs": []}
    rows, previous_end = [], None
    for start, end in segments:
        ici = None if previous_end is None else max(0.0, (start - previous_end) / SAMPLE_RATE)
        rows.append(extract_features(audio[start:end], ici, SAMPLE_RATE))
        previous_end = end
    scores = predict_scores(rows)
    coughs = [{
        "index": index,
        "start_sec": round(start / SAMPLE_RATE, 3),
        "end_sec": round(end / SAMPLE_RATE, 3),
        "positive_score": score,
    } for index, ((start, end), score) in enumerate(zip(segments, scores), start=1)]
    return {
        "cough_count": len(coughs),
        "average_positive_score": float(np.mean(scores)),
        "coughs": coughs,
    }


def analyze_uploaded_audio(uploaded_file):
    suffix, temporary_path = Path(uploaded_file.name).suffix.lower() or ".audio", None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            for chunk in uploaded_file.chunks():
                temporary.write(chunk)
        return analyze_audio_path(str(temporary_path))
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
