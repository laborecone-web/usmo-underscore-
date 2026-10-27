"""Synthesize a music bed + SFX synced to video.html scene timings. usage: python3 audio.py out.wav"""
import sys, wave
import numpy as np

SR = 44100
DUR = 28.5
BPM = 120
N = int(SR * DUR)
t_all = np.arange(N) / SR
mix = np.zeros(N)
rng = np.random.default_rng(3)

def add(sig, at, gain=1.0):
    i = int(at * SR)
    j = min(N, i + len(sig))
    if i < N:
        mix[i:j] += sig[: j - i] * gain

def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.12)

def hat():
    n = int(0.06 * SR)
    x = rng.standard_normal(n); x = np.diff(x, prepend=0)
    return x * env(n, 0.0005, 0.015)

def clap():
    n = int(0.2 * SR)
    x = rng.standard_normal(n) * env(n, 0.001, 0.05)
    return np.diff(x, prepend=0) * 0.8

def tone(freq, length, d=0.3, kind='saw'):
    n = int(length * SR); t = np.arange(n) / SR
    ph = (t * freq) % 1
    w = 2 * ph - 1 if kind == 'saw' else np.sin(2 * np.pi * freq * t)
    return w * env(n, 0.005, d)

def whoosh(length=0.45, up=True):
    n = int(length * SR)
    x = rng.standard_normal(n)
    # crude moving lowpass via cumulative smoothing with varying alpha
    a = np.linspace(0.02, 0.5, n) if up else np.linspace(0.5, 0.02, n)
    y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc += a[i] * (x[i] - acc); y[i] = acc
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    return y * shape * 1.8

def pop(freq=900):
    n = int(0.08 * SR); t = np.arange(n) / SR
    f = freq * (1 + 2 * np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.02)

def boom():
    n = int(1.2 * SR); t = np.arange(n) / SR
    f = 35 + 60 * np.exp(-t * 8)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.45)
            + rng.standard_normal(n) * env(n, 0.001, 0.08) * 0.4)

def riser(length):
    n = int(length * SR); t = np.arange(n) / SR
    f = 200 * (8 ** (t / length))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 + rng.standard_normal(n) * 0.15) * (t / length) ** 2

# --- music: A minor-ish groove (Am F C G) ---
beat = 60 / BPM
chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 164.81, 196.0), (196.0, 246.94, 293.66)]
bass = [55.0, 43.65, 65.41, 49.0]
end_music = 27.6
b = 0
while b * beat < end_music:
    at = b * beat
    bar = (b // 4) % 4
    intro = at < 1.0
    if not intro:
        add(kick(), at, 0.9)
        if b % 2 == 1: add(clap(), at, 0.35)
        add(hat(), at + beat / 2, 0.25)
        add(tone(bass[bar], beat * 0.9, 0.18), at, 0.22)
        add(tone(bass[bar] * 2, beat * 0.4, 0.08, 'sine'), at + beat / 2, 0.18)
    if b % 4 == 0:
        for f in chords[bar]:
            add(tone(f, beat * 4, 1.2, 'sine'), at, 0.08)
    # arp
    for k in range(2):
        f = chords[bar][(b * 2 + k) % 3] * 2
        add(tone(f, beat / 2, 0.08, 'sine'), at + k * beat / 2, 0.07)
    b += 1

# --- SFX synced to scene cuts / text pops ---
for cut in [3.4, 7.4, 11.6, 17.2, 21.2, 25.0]:
    add(whoosh(0.45), cut - 0.3, 0.35)
for at in [0.3, 1.0, 1.55, 1.67, 1.79, 3.8, 4.1, 4.4, 8.5, 8.9, 12.2, 15.6, 22.7, 26.2, 26.3, 26.4, 26.5, 26.6]:
    add(pop(800 + 300 * rng.random()), at, 0.25)
for i in range(4):
    add(pop(1200), 12.2 + i * 1.05, 0.3)
add(riser(1.2), 16.0, 0.3)
add(boom(), 18.7, 0.9)            # 2022 stamp
add(boom(), 21.6, 0.6)            # 2030
add(boom(), 25.35, 0.7)           # logo
add(pop(500), 5.4, 0.3)           # kick
for at in np.linspace(17.4, 18.5, 14):  # count-up ticks
    add(pop(1600), at, 0.12)

# master: fade, soft clip, normalize
fade = np.ones(N); fo = int(0.8 * SR); fade[-fo:] = np.linspace(1, 0, fo)
fade[: int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
mix = np.tanh(mix * fade * 1.2)
mix = mix / np.max(np.abs(mix)) * 0.9
stereo = np.stack([mix, np.roll(mix, 220) * 0.97], axis=1)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype('<i2').tobytes())
