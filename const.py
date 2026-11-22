from pathlib import Path

VOICE_DIR = Path.home() / "piper" / "voices"
ENG_MODEL = [
    {"name": "en_US-lessac-medium.onnx", "speaker": None},
    {"name": "en_US-libritts_r-medium.onnx", "speaker": [range(-904, 904)]},
]
FR_MODEL = []

