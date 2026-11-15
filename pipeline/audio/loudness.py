"""Rough LUFS-like normalization (peak -1.5 dB, RMS ~ -14)."""
import math

def normalize(samples, target_rms_db=-14.0, peak_db=-1.5):
    if not samples:
        return samples
    rms = math.sqrt(sum(s * s for s in samples) / len(samples) + 1e-12)
    rms_db = 20 * math.log10(rms + 1e-12)
    gain = 10 ** ((target_rms_db - rms_db) / 20)
    peak = max(abs(s) for s in samples) * gain
    peak_limit = 10 ** (peak_db / 20)
    if peak > peak_limit:
        gain *= peak_limit / peak
    return [s * gain for s in samples]