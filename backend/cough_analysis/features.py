"""The 123 non-active features used by the infectious-disease classifier."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000
FEATURE_COLUMNS = ["Duration", "ici_prev_s"] + [
    "rise_time", "decay_time", "decay_rate", "rms_mean", "rms_std",
    "zcr_mean", "zcr_std", "Centroid_mean", "Centroid_std",
    "bandwidth_mean", "bandwidth_std", "Rolloff_mean", "Rolloff_std",
    "Flatness_mean", "Flatness_std",
] + [v for i in range(40) for v in (f"melband_{i:02d}_mean", f"melband_{i:02d}_std")] + [
    v for i in range(13) for v in (f"mfcc_{i:02d}_mean", f"mfcc_{i:02d}_std")
]


def load_audio(path: str) -> np.ndarray:
    import librosa

    try:
        audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True)
    except Exception as original_error:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise ValueError("Audio codec is unsupported and ffmpeg is not installed.") from original_error
        converted_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as converted:
                converted_path = Path(converted.name)
            subprocess.run(
                [ffmpeg, "-nostdin", "-v", "error", "-y", "-i", path,
                 "-ac", "1", "-ar", str(SAMPLE_RATE), str(converted_path)],
                check=True,
                capture_output=True,
                timeout=60,
            )
            audio, _ = librosa.load(str(converted_path), sr=SAMPLE_RATE, mono=True)
        except (subprocess.SubprocessError, OSError) as conversion_error:
            raise ValueError("Audio could not be decoded with ffmpeg.") from conversion_error
        finally:
            if converted_path is not None:
                converted_path.unlink(missing_ok=True)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError("Audio is empty or invalid.")
    return audio.astype(np.float32)


def _rise_decay(segment: np.ndarray, sr: int):
    absolute = np.abs(segment)
    peak = float(absolute.max()) if absolute.size else 0.0
    if peak == 0:
        return None, None, None
    normalized = absolute / peak
    p10, p90 = np.flatnonzero(normalized >= .1), np.flatnonzero(normalized >= .9)
    rise = float((p90[0] - p10[0]) / sr) if p10.size and p90.size and p90[0] > p10[0] else None
    decay = None
    if p90.size:
        below = np.flatnonzero(normalized[p90[-1]:] < .1)
        decay = float(below[0] / sr) if below.size else None
    peak_index = int(np.argmax(absolute))
    duration = (len(segment) - 1 - peak_index) / sr
    rate = None
    if duration > 0 and absolute[-1] > 0:
        ratio = float(absolute[-1] / peak)
        rate = float(-np.log(ratio) / duration) if 0 < ratio < 1 else (0.0 if ratio >= 1 else None)
    return rise, decay, rate


def extract_features(segment: np.ndarray, ici_prev_s: float | None, sr: int = SAMPLE_RATE):
    """Match coughs共有用/卒論関連/features/acoustic_features.py."""
    import librosa

    if not segment.size:
        raise ValueError("Cough segment is empty.")
    hop = int(.01 * sr)
    result = {"Duration": float(len(segment) / sr), "ici_prev_s": ici_prev_s}
    rise, decay, rate = _rise_decay(segment, sr)
    result.update(rise_time=rise, decay_time=decay, decay_rate=rate)
    rms = librosa.feature.rms(y=segment, hop_length=hop)[0]
    peak_rms = float(rms.max()) if rms.size else 0.0
    normalized_rms = rms / peak_rms if peak_rms > 0 else None
    result["rms_mean"] = float(np.mean(normalized_rms)) if normalized_rms is not None else None
    result["rms_std"] = float(np.std(normalized_rms)) if normalized_rms is not None else None
    zcr = librosa.feature.zero_crossing_rate(y=segment, hop_length=hop)[0]
    result.update(zcr_mean=float(zcr.mean()), zcr_std=float(zcr.std()))
    spectrum = np.abs(librosa.stft(segment, n_fft=512, hop_length=hop))
    series = {
        "Centroid": librosa.feature.spectral_centroid(S=spectrum, sr=sr)[0],
        "bandwidth": librosa.feature.spectral_bandwidth(S=spectrum, sr=sr)[0],
        "Rolloff": librosa.feature.spectral_rolloff(S=spectrum, sr=sr)[0],
        "Flatness": librosa.feature.spectral_flatness(S=spectrum)[0],
    }
    for name, values in series.items():
        result[f"{name}_mean"], result[f"{name}_std"] = float(values.mean()), float(values.std())
    mel = librosa.feature.melspectrogram(y=segment, sr=sr, n_mels=40, hop_length=hop)
    total = float(mel.sum())
    means = mel.sum(axis=1) / total if total > 0 else np.zeros(40)
    stds = np.std(librosa.power_to_db(mel / total, ref=np.max), axis=1) if total > 0 else np.zeros(40)
    for i in range(40):
        result[f"melband_{i:02d}_mean"], result[f"melband_{i:02d}_std"] = float(means[i]), float(stds[i])
    mfcc = librosa.feature.mfcc(y=segment, sr=sr, n_mfcc=13, hop_length=hop)
    for i in range(13):
        result[f"mfcc_{i:02d}_mean"], result[f"mfcc_{i:02d}_std"] = float(mfcc[i].mean()), float(mfcc[i].std())
    return {column: result.get(column) for column in FEATURE_COLUMNS}
