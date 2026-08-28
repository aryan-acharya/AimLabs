"""
game/sound.py - Sound effects manager
Loads gun/reload sounds from fixed files in game/sounds;
falls back to procedural generation if a file is missing.
"""
import os
import numpy as np
import pygame


# Path to sounds folder
_SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds')


# Fallback: procedurally generated gunshot
def _generate_shoot_sound(sample_rate=44100, duration=0.18):
    """Punchy gunshot transient (used only when no sound file is found)."""
    if not pygame.mixer.get_init():
        return None

    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    noise    = np.random.uniform(-1.0, 1.0, n)
    envelope = np.exp(-t * 45.0)
    body     = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 30.0)

    signal = np.clip(noise * envelope * 0.7 + body * 0.5, -1.0, 1.0)
    samples = (signal * 32767).astype(np.int16)
    stereo  = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(stereo)



def _generate_reload_sound(sample_rate=44100, duration=0.12):
    """Mechanical click / clack for magazine insert."""
    if not pygame.mixer.get_init():
        return None
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    # sharp transient click + short noise burst
    click   = np.sin(2 * np.pi * 300 * t) * np.exp(-t * 80.0)
    noise   = np.random.uniform(-1.0, 1.0, n) * np.exp(-t * 60.0) * 0.6
    signal  = np.clip(click + noise, -1.0, 1.0)
    samples = (signal * 28000).astype(np.int16)
    stereo  = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(stereo)


def _generate_hit_sound(sample_rate=44100, duration=0.08):
    """Short metallic ping for hit confirmation."""
    if not pygame.mixer.get_init():
        return None

    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    tone = np.sin(2 * np.pi * 1200.0 * t) * np.exp(-t * 50.0)
    tone = np.clip(tone, -1.0, 1.0)

    samples = (tone * 20000).astype(np.int16)
    stereo  = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(stereo)


# SoundManager
class SoundManager:
    def __init__(self):
        self.shoot_sound  = None
        self.hit_sound    = None
        self.reload_sound = None

        if not pygame.mixer.get_init():
            return

        # Load shoot sound from fixed file name
        sound_file = os.path.join(_SOUNDS_DIR, 'shot_sound.mp3')

        if os.path.isfile(sound_file):
            try:
                self.shoot_sound = pygame.mixer.Sound(sound_file)
            except Exception:
                self.shoot_sound = _generate_shoot_sound()
        else:
            self.shoot_sound = _generate_shoot_sound()

        # Hit confirmation (always procedural)
        self.hit_sound = _generate_hit_sound()

        # Load reload sound from fixed file name
        reload_file = os.path.join(_SOUNDS_DIR, 'reload.mp3')

        if os.path.isfile(reload_file):
            try:
                self.reload_sound = pygame.mixer.Sound(reload_file)
            except Exception:
                self.reload_sound = _generate_reload_sound()
        else:
            self.reload_sound = _generate_reload_sound()

        if self.shoot_sound:
            self.shoot_sound.set_volume(0.80)
        if self.hit_sound:
            self.hit_sound.set_volume(0.55)
        if self.reload_sound:
            self.reload_sound.set_volume(0.70)

    def play_shoot(self):
        if self.shoot_sound:
            self.shoot_sound.play()

    def play_hit(self):
        if self.hit_sound:
            self.hit_sound.play()

    def play_reload(self):
        if self.reload_sound:
            self.reload_sound.play()
