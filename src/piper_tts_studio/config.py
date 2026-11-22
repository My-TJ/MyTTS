from pathlib import Path

VOICE_DIR = Path.home() / "piper" / "voices"

ENG_MODEL = (
    {"name": "en_US-lessac-medium.onnx", "speaker": None},
    {"name": "en_US-libritts_r-medium.onnx", "speaker": (0, 903)},
)
FR_MODEL = ()

SPEED_PRESETS = {
    "slow": 1.25,
    "normal": 1.00,
    "fast": 0.75,
}

PREVIEW_TEXT = (
    "Hello, this is a sample of my voice. "
    "Listen carefully and choose the speaker you prefer."
)
