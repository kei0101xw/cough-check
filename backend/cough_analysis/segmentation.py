"""CNN cough segmentation derived from coughs共有用/nicholas."""

import numpy as np

SAMPLE_RATE, N_FFT, HOP_LENGTH = 16_000, 128, 64
CHUNK_WIDTH, OVERLAP = 128, 112
ON_THRESHOLD, OFF_THRESHOLD = .97, .70


def build_model():
    from tensorflow import keras

    inputs = keras.Input((64, 128, 1))
    x = keras.layers.GaussianNoise(.025)(inputs)
    for filters, kernel, pool in [(64, 7, None), (64, 5, (2, 4)), (128, 3, (2, 2)), (128, 3, (2, 2)), (128, 3, (2, 2))]:
        x = keras.layers.Conv2D(filters, kernel, padding="same")(x)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.SpatialDropout2D(.20)(x)
        if pool:
            x = keras.layers.MaxPooling2D(pool, strides=pool, padding="same")(x)
        x = keras.layers.Activation("relu")(x)
    branches = []
    for activation in ("sigmoid", "softmax"):
        branch = keras.layers.Conv2D(256, 3, padding="same")(x)
        branch = keras.layers.BatchNormalization()(branch)
        branch = keras.layers.SpatialDropout2D(.20)(branch)
        branches.append(keras.layers.Flatten()(keras.layers.Activation(activation)(branch)))
    x = keras.layers.Multiply()(branches)
    x = keras.layers.Dense(256, name="dense_2")(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Dropout(.20)(x)
    x = keras.layers.Activation("sigmoid")(x)
    output = keras.layers.Activation("sigmoid", name="output")(keras.layers.Dense(1, name="dense_3")(x))
    return keras.Model(inputs, output, name="CustCGANN")


def _chunks(audio):
    import librosa

    power = np.abs(librosa.stft(audio, n_fft=N_FFT, hop_length=HOP_LENGTH)) ** 2
    if not power.size or power.max() <= 0:
        return np.empty((0, 64, CHUNK_WIDTH, 1), dtype=np.float32)
    power /= power.max()
    db = librosa.power_to_db(power, ref=1.0)
    denominator = float((db - 20).max())
    if denominator == 0:
        return np.empty((0, 64, CHUNK_WIDTH, 1), dtype=np.float32)
    spec, step, blocks = ((db - 20) / denominator)[1:], CHUNK_WIDTH - OVERLAP, []
    for start in range(0, spec.shape[1], step):
        block = spec[:, start:start + CHUNK_WIDTH]
        if block.shape[1] < CHUNK_WIDTH:
            block = np.pad(block, ((0, 0), (0, CHUNK_WIDTH - block.shape[1])))
        blocks.append(block[..., None])
        if start + CHUNK_WIDTH >= spec.shape[1]:
            break
    return np.asarray(blocks, dtype=np.float32)


def detect_segments(audio, model):
    chunks = _chunks(audio)
    if not len(chunks):
        return []
    probabilities = np.asarray(model.predict(chunks, verbose=0)).reshape(-1)
    chunk_intervals, start = [], None
    for index, probability in enumerate(probabilities):
        if start is None and probability > ON_THRESHOLD:
            start = index
        elif start is not None and probability < OFF_THRESHOLD:
            chunk_intervals.append((start, index)); start = None
    if start is not None:
        chunk_intervals.append((start, len(probabilities)))
    step_samples, window_samples = (CHUNK_WIDTH - OVERLAP) * HOP_LENGTH, CHUNK_WIDTH * HOP_LENGTH
    merged = []
    for start, end in chunk_intervals:
        interval = [start * step_samples, min(len(audio), (end - 1) * step_samples + window_samples)]
        if interval[1] <= interval[0]:
            continue
        if merged and interval[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], interval[1])
        else:
            merged.append(interval)
    return [tuple(interval) for interval in merged]
