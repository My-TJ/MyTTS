import datetime
import re
import shutil
import tempfile
import wave
from pathlib import Path

from piper import PiperVoice
from piper.config import SynthesisConfig


def split_text(text: str, max_chars: int = 900) -> list[str]:
    """Split text at paragraph, sentence, or word boundaries."""
    if not 100 <= max_chars <= 1500:
        raise ValueError("Chunk size must be from 100 through 1500 characters.")

    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]

    for paragraph in paragraphs:
        remaining = re.sub(r"\s+", " ", paragraph).strip()
        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining)
                break

            window = remaining[: max_chars + 1]
            sentence_matches = re.finditer(r"[.!?](?:[\"'”)]*)\s", window)
            sentence_boundary = max((match.end() for match in sentence_matches), default=-1)

            if sentence_boundary > 100:
                boundary = sentence_boundary
            else:
                boundary = remaining.rfind(" ", 100, max_chars + 1)
                if boundary < 1:
                    boundary = max_chars

            chunk = remaining[:boundary].strip()
            if not chunk:
                chunk = remaining[:max_chars].strip()
                boundary = len(chunk)

            chunks.append(chunk)
            remaining = remaining[boundary:].strip()

    return chunks


def concatenate_wav_files(source_paths: list[Path], output_path: Path) -> None:
    if not source_paths:
        raise ValueError("No WAV chunks were produced.")

    with wave.open(str(source_paths[0]), "rb") as first:
        channels = first.getnchannels()
        sample_width = first.getsampwidth()
        sample_rate = first.getframerate()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(sample_width)
        output.setframerate(sample_rate)
        for source_path in source_paths:
            with wave.open(str(source_path), "rb") as source:
                output.writeframes(source.readframes(source.getnframes()))


def create_transcript_folder(base_output: Path, title: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-").lower() or "transcript"
    folder = base_output.parent / f"{safe_title}-{timestamp}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def synthesize_document(
    voice: PiperVoice,
    text: str,
    output_path: str,
    speaker_id: int,
    length_scale: float,
    save_artifacts: bool = False,
    title: str = "transcript",
    chunk_size: int = 900,
    save_dir: Path | None = None,
) -> tuple[Path, list[Path], Path | None]:
    text = text.strip()
    if not text:
        raise ValueError("Text cannot be empty.")

    chunks = split_text(text, chunk_size)
    base_output = Path(output_path).expanduser()

    storage_output = save_dir.expanduser() / base_output.name if save_dir else base_output
    storage_output.parent.mkdir(parents=True, exist_ok=True)
    artifact_folder = create_transcript_folder(storage_output, title) if save_artifacts else None
    final_output = artifact_folder / base_output.name if artifact_folder else base_output

    syn_config = SynthesisConfig(speaker_id=speaker_id, length_scale=length_scale)

    with tempfile.TemporaryDirectory(prefix="piper-document-") as temp_dir:
        temp_paths: list[Path] = []
        for index, chunk in enumerate(chunks, start=1):
            chunk_path = Path(temp_dir) / f"chunk-{index:04d}.wav"
            with wave.open(str(chunk_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(22050)
                voice.synthesize_wav(chunk, wav_file, syn_config)
            temp_paths.append(chunk_path)

            if artifact_folder:
                shutil.copy2(chunk_path, artifact_folder / chunk_path.name)

        concatenate_wav_files(temp_paths, final_output)

    if artifact_folder:
        (artifact_folder / "transcript.txt").write_text(text, encoding="utf-8")
        (artifact_folder / "manifest.txt").write_text(
            f"title={title}\nchunks={len(chunks)}\nspeaker={speaker_id}\n"
            f"length_scale={length_scale}\noutput={final_output.name}\n",
            encoding="utf-8",
        )

    chunk_paths = (
        [artifact_folder / f"chunk-{index:04d}.wav" for index in range(1, len(chunks) + 1)]
        if artifact_folder
        else []
    )
    return final_output, chunk_paths, artifact_folder
