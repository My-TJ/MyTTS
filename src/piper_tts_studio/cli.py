import argparse
import shutil
import subprocess
import wave
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from piper import PiperVoice

from .config import ENG_MODEL, PREVIEW_TEXT, SPEED_PRESETS, VOICE_DIR
from .document import synthesize_document

console = Console()


def get_length_scale(value: str) -> float:
    value = value.lower().strip()
    if value in SPEED_PRESETS:
        return SPEED_PRESETS[value]
    try:
        scale = float(value)
    except ValueError as exc:
        raise ValueError("Use slow, normal, fast, or a numeric scale from 0.5 to 2.0.") from exc
    if not 0.5 <= scale <= 2.0:
        raise ValueError("Numeric scale must be from 0.5 to 2.0.")
    return scale


def validate_speaker(model_index: int, speaker_id: int) -> int:
    if model_index == 0:
        if speaker_id != 0:
            console.print("Lessac is single-speaker; using speaker 0.", style="yellow")
        return 0
    if not 0 <= speaker_id <= 903:
        raise ValueError("LibriTTS speaker ID must be from 0 through 903.")
    return speaker_id


def find_player() -> str | None:
    return next((player for player in ("paplay", "aplay", "ffplay") if shutil.which(player)), None)


def play(path: Path, player: str | None, no_play: bool) -> None:
    if no_play:
        return
    if not player:
        console.print("No supported audio player found.", style="red")
        return
    command = [player]
    if player == "ffplay":
        command += ["-nodisp", "-autoexit", "-loglevel", "error"]
    subprocess.run(command + [str(path)], check=False)


def preview(voice: PiperVoice, model_index: int, count: int, scale: float, player: str | None, no_play: bool) -> None:
    if count < 1 or count > 20:
        raise ValueError("Preview count must be from 1 through 20.")
    ids = [0] if model_index == 0 or count == 1 else sorted({round(i * 903 / (count - 1)) for i in range(count)})
    console.print(Panel(PREVIEW_TEXT, title="Speaker Preview", border_style="cyan"))
    import tempfile
    with tempfile.TemporaryDirectory(prefix="piper-preview-") as directory:
        for index, speaker_id in enumerate(ids, start=1):
            preview_path = Path(directory) / f"speaker-{speaker_id}.wav"
            console.print(f"[yellow]Preview {index}/{len(ids)}[/] — Speaker [cyan]{speaker_id}[/]")
            synthesize_document(voice, PREVIEW_TEXT, str(preview_path), speaker_id, scale)
            play(preview_path, player, no_play)


def print_status(model_index: int, speaker_id: int, scale: float, output: str) -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(style="cyan")
    table.add_column(style="bold")
    table.add_row("Model", ENG_MODEL[model_index]["name"])
    table.add_row("Speaker", str(speaker_id))
    table.add_row("Length scale", str(scale))
    table.add_row("Output", output)
    console.print(Panel(table, title="Current Configuration", border_style="cyan"))


def print_help() -> None:
    table = Table(title="Interactive Commands", border_style="blue")
    table.add_column("Command", style="yellow")
    table.add_column("Description")
    for command, description in (
        ("<text>", "Synthesize text"),
        ("/source <file>", "Load a UTF-8 text file"),
        ("/speed <value>", "Set pace"),
        ("/speaker <id>", "Set speaker"),
        ("/model <index>", "Select model"),
        ("/preview [count]", "Preview representative voices"),
        ("/save on|off", "Enable transcript artifacts"),
        ("/title <name>", "Set artifact title"),
        ("/status", "Show configuration"),
        ("/help", "Show commands"),
        ("/quit", "Exit"),
    ):
        table.add_row(command, description)
    console.print(table)


def interactive(args: argparse.Namespace) -> None:
    scale = get_length_scale(args.speed)
    model_index = args.model
    speaker_id = validate_speaker(model_index, args.speaker)
    voice = PiperVoice.load(VOICE_DIR / ENG_MODEL[model_index]["name"])
    player = find_player()
    save_artifacts = False
    transcript_title = args.title
    session = PromptSession(history=InMemoryHistory())

    console.print(Panel.fit("Piper TTS Studio\nInteractive voice synthesis", border_style="cyan"))
    print_status(model_index, speaker_id, scale, args.output)

    while True:
        try:
            entered = session.prompt("piper> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not entered:
            continue
        if not entered.startswith("/"):
            try:
                final, chunks, folder = synthesize_document(
                    voice, entered, args.output, speaker_id, scale,
                    save_artifacts, transcript_title, args.chunk_size, args.save_dir,
                )
                console.print(Panel.fit(f"Saved: {final}\nChunks: {len(chunks)}", border_style="green"))
                play(final, player, args.no_play)
            except Exception as exc:
                console.print(f"Synthesis error: {exc}", style="red")
            continue

        parts = entered.split(maxsplit=1)
        command = parts[0].lower()
        value = parts[1].strip() if len(parts) == 2 else ""
        if command in ("/quit", "/exit"):
            break
        if command == "/help":
            print_help()
        elif command == "/status":
            print_status(model_index, speaker_id, scale, args.output)
        elif command == "/speed":
            try:
                scale = get_length_scale(value)
                console.print(f"Speed updated: {scale}", style="green")
            except ValueError as exc:
                console.print(str(exc), style="red")
        elif command == "/speaker":
            try:
                speaker_id = validate_speaker(model_index, int(value))
                console.print(f"Speaker updated: {speaker_id}", style="green")
            except (ValueError, TypeError) as exc:
                console.print(str(exc), style="red")
        elif command == "/model":
            try:
                model_index = int(value)
                if not 0 <= model_index < len(ENG_MODEL):
                    raise ValueError("Model index is out of range.")
                voice = PiperVoice.load(VOICE_DIR / ENG_MODEL[model_index]["name"])
                speaker_id = validate_speaker(model_index, speaker_id)
                console.print("Model updated.", style="green")
            except (ValueError, OSError) as exc:
                console.print(str(exc), style="red")
        elif command == "/preview":
            try:
                preview(voice, model_index, int(value) if value else 5, scale, player, args.no_play)
            except (ValueError, TypeError) as exc:
                console.print(str(exc), style="red")
        elif command == "/source":
            source = Path(value).expanduser()
            if not source.is_file():
                console.print(f"Source not found: {source}", style="red")
            else:
                try:
                    final, chunks, folder = synthesize_document(
                        voice, source.read_text(encoding="utf-8"), args.output,
                        speaker_id, scale, save_artifacts, transcript_title,
                        args.chunk_size, args.save_dir,
                    )
                    console.print(Panel.fit(f"Source: {source}\nSaved: {final}\nChunks: {len(chunks)}", border_style="green"))
                    play(final, player, args.no_play)
                except Exception as exc:
                    console.print(f"Synthesis error: {exc}", style="red")
        elif command == "/save":
            if value.lower() in ("on", "off"):
                save_artifacts = value.lower() == "on"
                console.print(f"Save transcripts: {value.lower()}", style="green")
            else:
                console.print("Use /save on or /save off", style="red")
        elif command == "/title":
            transcript_title = value or transcript_title
            console.print(f"Transcript title: {transcript_title}", style="green")
        else:
            console.print(f"Unknown command: {command}", style="red")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Piper TTS Studio")
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--speed", default="normal")
    parser.add_argument("--speaker", type=int, default=23)
    parser.add_argument("--model", type=int, choices=range(len(ENG_MODEL)), default=1)
    parser.add_argument("--output", default="output.wav")
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--preview-count", type=int, default=5)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--save-dir", type=Path, default=Path("transcripts"))
    parser.add_argument("--title", default="transcript")
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("text", nargs="*")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.interactive:
        interactive(args)
        return

    scale = get_length_scale(args.speed)
    speaker = validate_speaker(args.model, args.speaker)
    voice = PiperVoice.load(VOICE_DIR / ENG_MODEL[args.model]["name"])
    if args.preview:
        preview(voice, args.model, args.preview_count, scale, find_player(), args.no_play)
        return

    if args.source:
        if not args.source.is_file():
            raise SystemExit(f"Source file not found: {args.source}")
        text = args.source.read_text(encoding="utf-8")
    else:
        text = " ".join(args.text).strip() or "Hello Mr Johnson. And welcome!"

    final, chunks, folder = synthesize_document(
        voice, text, args.output, speaker, scale,
        args.save, args.title, args.chunk_size, args.save_dir,
    )
    console.print(f"Audio synthesis complete: {final}", style="green")
    if folder:
        console.print(f"Transcript folder: {folder}", style="cyan")
    play(final, find_player(), args.no_play)


if __name__ == "__main__":
    main()
