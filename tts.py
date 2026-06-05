"""tts.py — local Kokoro-82M text-to-speech (Apache-2.0), vendored so the standalone
Enigma Avatar speaks without the rest of the Modkit voice mod. 100% local, no cloud.

Install once (no admin):
    python -m pip install --user kokoro soundfile numpy

Used by speak.py and avatar_mcp.py to synthesize a WAV; the overlay then plays it
over the bus and lip-syncs the mouth to the audio (see avatar.js `speak`).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger("avatar.tts")
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

DEFAULT_KOKORO_VOICES = (
    "af_heart", "af_bella", "af_sarah",
    "am_adam", "am_michael",
    "bf_emma", "bf_isabella",
    "bm_george", "bm_lewis",
)


class LocalTTS:
    """Local TTS via Kokoro-82M (extracted from the Modkit voice mod's LocalTTS)."""

    def __init__(self, voice: str = "af_heart", lang_code: str = "a", speed: float = 1.0) -> None:
        self.voice = voice
        self.lang_code = lang_code
        self.speed = float(speed)
        self._pipeline: Any = None
        self._sf: Any = None

    def _ensure_imports(self) -> bool:
        if self._pipeline is not None:
            return True
        try:
            from kokoro import KPipeline
            self._pipeline = KPipeline(lang_code=self.lang_code)
            return True
        except Exception as e:
            logger.error(f"kokoro not available (pip install --user kokoro): {e}")
            return False

    def _ensure_io(self) -> bool:
        try:
            if self._sf is None:
                import soundfile as sf
                self._sf = sf
            return True
        except Exception as e:
            logger.error(f"soundfile not available (pip install --user soundfile): {e}")
            return False

    def load(self) -> bool:
        return self._ensure_imports()

    def generate_to_file(self, text: str, out_path: Optional[Path] = None) -> Optional[Path]:
        if not self._ensure_imports() or not self._ensure_io():
            return None
        try:
            if out_path is None:
                out_path = OUTPUT_DIR / f"speech_{int(time.time() * 1000)}.wav"
            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            chunks: List[Any] = []
            for _i, _ps, audio in self._pipeline(text, voice=self.voice, speed=self.speed):
                arr = audio.numpy() if hasattr(audio, "numpy") else audio
                chunks.append(arr)
            if not chunks:
                return None
            import numpy as np
            data = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
            self._sf.write(str(out_path), data, 24000)
            return out_path
        except Exception as e:
            logger.error(f"LocalTTS.generate_to_file failed: {e}")
            return None

    def get_voices(self) -> List[str]:
        return list(DEFAULT_KOKORO_VOICES)
