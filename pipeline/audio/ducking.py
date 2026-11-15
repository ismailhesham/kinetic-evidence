"""Sidechain ducking helper (envelope follower)."""
def apply_duck(voice_samples, bed_samples, threshold=0.01, ratio=0.5):
    out = []
    for i in range(len(voice_samples)):
        v = voice_samples[i]
        b = bed_samples[i] if i < len(bed_samples) else 0.0
        gain = ratio if abs(v) > threshold else 1.0
        out.append(b * gain)
    return out