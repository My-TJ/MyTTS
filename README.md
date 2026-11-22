# Piper Text-to-Speech Documentation

This document describes Piper usage in this repository. It is based on the installed **piper-tts 1.8.0** package and voice models stored in `~/piper/voices/`.

## Overview

Piper converts text into 22.05 kHz 16-bit mono WAV audio using an ONNX voice model. This project loads voices through `PiperVoice` and can select a voice or speaker through `SynthesisConfig`.

## Voice Configuration

`MyTTS/const.py` defines:

- `VOICE_DIR`: the directory containing Piper ONNX models and JSON configuration files.
- `ENG_MODEL`: available English models.
- `FR_MODEL`: reserved French models.

Current English models:

| Index | Model | Speakers |
|---|---|---:|
| `0` | `en_US-lessac-medium.onnx` | Single voice |
| `1` | `en_US-libritts_r-medium.onnx` | 904 voices |

The model index and the speaker index are different:

- `ENG_MODEL[0]` selects the Lessac model.
- `ENG_MODEL[1]` selects the LibriTTS multi-speaker model.
- `SynthesisConfig(speaker_id=23)` selects speaker 23 within the LibriTTS model.

For `en_US-libritts_r-medium.onnx`, valid internal speaker IDs are `0` through `903`.

## Installation

Activate the project Python environment, then install Piper if needed:

```bash
source .venv/bin/activate
pip install piper-tts
```

Piper requires both files for a voice:

```text
model.onnx
model.onnx.json
```

The JSON file may be inferred automatically when the model path is provided. It must have the same base name as the ONNX file.

## Basic Usage

```python
from pathlib import Path
import wave

from piper import PiperVoice

model_path = Path.home() / "piper" / "voices" / "en_US-lessac-medium.onnx"
voice = PiperVoice.load(model_path)

with wave.open("output.wav", "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(22050)
    voice.synthesize_wav("Hello, this is Piper.", wav_file)
```

## Using a Specific Speaker

```python
from pathlib import Path
import wave

from piper import PiperVoice
from piper.config import SynthesisConfig

model_path = Path.home() / "piper" / "voices" / "en_US-libritts_r-medium.onnx"
voice = PiperVoice.load(model_path)
syn_config = SynthesisConfig(speaker_id=23)

with wave.open("speaker-23.wav", "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(22050)
    voice.synthesize_wav(
        "Hello Mr D.C.T. and welcome!",
        wav_file,
        syn_config,
    )
```

To use speaker 900:

```python
syn_config = SynthesisConfig(speaker_id=900)
```

Do not pass `23` or `900` to `ENG_MODEL` as a list index. `ENG_MODEL[23]` would try to access a model that does not exist.

## Repository Example

`MyTTS/piper_test.py` currently demonstrates the multi-speaker model:

```python
voice = PiperVoice.load(VOICE_DIR / ENG_MODEL[1]["name"])
syn_config = SynthesisConfig(speaker_id=23)

with wave.open("output.wav", "wb") as wav_file:
    voice.synthesize_wav(text, wav_file, syn_config)
```

Change `speaker_id` to select another speaker, for example `0`, `23`, or `900`.

## Loading a Model

```python
PiperVoice.load(
    model_path,
    config_path=None,
    use_cuda=False,
    espeak_data_dir=None,
    download_dir=None,
    include_alignments=False,
)
```

Parameters:

- `model_path`: path to the `.onnx` model.
- `config_path`: optional path to the model JSON. Piper usually finds `<model_path>.json` automatically.
- `use_cuda`: enables CUDA inference when supported.
- `espeak_data_dir`: optional eSpeak-NG data directory.
- `download_dir`: optional directory for downloadable resources.
- `include_alignments`: enables phoneme alignment generation.

## Synthesis Configuration

`SynthesisConfig` controls speaker and synthesis parameters:

```python
SynthesisConfig(
    speaker_id=None,
    length_scale=None,
    noise_scale=None,
    noise_w_scale=None,
    normalize_audio=True,
    volume=1.0,
)
```

Parameters:

- `speaker_id`: speaker index for a multi-speaker model.
- `length_scale`: controls speech duration. Larger values generally produce slower speech.
- `noise_scale`: controls variation in the generated audio.
- `noise_w_scale`: controls phoneme-width variation.
- `normalize_audio`: normalizes the resulting audio when enabled.
- `volume`: scales the output volume. `1.0` uses normal volume.

Example:

```python
syn_config = SynthesisConfig(
    speaker_id=23,
    length_scale=1.0,
    noise_scale=0.667,
    noise_w_scale=0.8,
    normalize_audio=True,
    volume=1.0,
)
```

## Synthesis Methods

### `synthesize_wav()`

Writes audio directly to an open WAV file:

```python
voice.synthesize_wav(text, wav_file, syn_config)
```

The method signature is:

```python
voice.synthesize_wav(
    text,
    wav_file,
    syn_config=None,
    set_wav_format=True,
    include_alignments=False,
)
```

Set `include_alignments=True` to receive a list of phoneme alignment objects when available.

### `synthesize()`

Returns an iterable of `AudioChunk` objects instead of writing a WAV file:

```python
for chunk in voice.synthesize(text, syn_config):
    print(chunk.sample_rate, chunk.sample_width, len(chunk.audio_int16_bytes))
```

This is useful for streaming or custom audio pipelines.

## Inspecting a Loaded Model

```python
voice = PiperVoice.load(model_path)

print(voice.config.num_speakers)
print(voice.config.num_symbols)
print(voice.config.sample_rate)
print(voice.config.speaker_id_map)
print(voice.config.default_speaker_id)
```

Important fields:

- `num_speakers`: number of available speakers.
- `sample_rate`: model sample rate.
- `speaker_id_map`: mapping used by named speakers in the model configuration.
- `default_speaker_id`: fallback speaker ID.

The local LibriTTS model reports:

- `num_speakers = 904`
- `sample_rate = 22050`
- `speaker_id_map` containing 904 entries

## WAV Output

Piper output should be configured consistently:

```python
wav_file.setnchannels(1)
wav_file.setsampwidth(2)
wav_file.setframerate(22050)
```

These settings represent:

- one channel (mono)
- two bytes per sample (16-bit)
- 22,050 samples per second

Change the sample rate only if the selected model uses a different one. The models currently used here use 22,050 Hz.

## Streaming Text

For applications that want streamed audio chunks:

```python
syn_config = SynthesisConfig(speaker_id=23)

for chunk in voice.synthesize("Streaming synthesis example.", syn_config):
    audio_bytes = chunk.audio_int16_bytes
```

The exact chunking behavior may differ for each model and synthesis call.

## CUDA

CUDA support can be requested during model loading:

```python
voice = PiperVoice.load(model_path, use_cuda=True)
```

This depends on the installed ONNX Runtime package and an available compatible CUDA environment. If CUDA is unavailable, load with `use_cuda=False`.

## Troubleshooting

### `ModuleNotFoundError: No module named 'piper'`

The package is installed in a different Python environment. Run with the environment that contains Piper:

```bash
python piper_test.py
```

### `IndexError: list index out of range`

This occurs when indexing `ENG_MODEL` with a model number that does not exist. The available English model indexes are `0` and `1`.

Use:

```python
ENG_MODEL[1]
```

for the LibriTTS model.

### Speaker ID Not Valid

For the Lessac model, no multi-speaker `speaker_id` should be used.

For the LibriTTS model, use a speaker ID from `0` through `903`:

```python
syn_config = SynthesisConfig(speaker_id=900)
```

### No Audio File Is Created

Verify that:

- the ONNX model and JSON file exist,
- the output directory is writable,
- the WAV file is opened successfully,
- Piper is running in the correct Python environment.

### Missing Model Configuration

Place the JSON next to the ONNX file using the matching filename:

```text
en_US-libritts_r-medium.onnx
en_US-libritts_r-medium.onnx.json
```

## Example Project Structure

```text
MyTTS/
├── const.py
├── piper_test.py
└── README.md
```

## Speed Manager

`MyTTS/piper_test.py` accepts command-line options to adjust speech pace, speaker, and output filename.

### Speech Speed Presets

| Argument | Piper `length_scale` | Pace |
|---|---:|---|
| `slow` | `1.25` | Slower |
| `normal` | `1.00` | Default |
| `fast` | `0.75` | Faster |

Piper's `length_scale` is inverse in practice: a larger value makes speech slower, while a smaller value makes it faster.

### Command-Line Examples

Run from `MyTTS/`:

```bash
python piper_test.py --speed slow
python piper_test.py --speed normal
python piper_test.py --speed fast
```

Use a numeric `length_scale` for finer control:

```bash
python piper_test.py --speed 1.40
python piper_test.py --speed 0.60
```

Numeric values must be between `0.5` and `2.0`.

Select a speaker and output filename too:

```bash
python piper_test.py --speed fast --speaker 900 --output fast-900.wav
```

Display all available command-line options:

```bash
python piper_test.py --help
```

### Speed Implementation

The script maps speed names to Piper values:

```python
SPEED_PRESETS = {
    "slow": 1.25,
    "normal": 1.00,
    "fast": 0.75,
}
```

It converts the selected speed into `SynthesisConfig.length_scale`:

```python
syn_config = SynthesisConfig(
    speaker_id=args.speaker,
    length_scale=length_scale,
)
```

The manager rejects unknown names and numeric values outside `0.5` through `2.0`, preventing unsupported synthesis configurations.

## Interactive Mode

Start a persistent session so configuration and text can be changed without restarting the script:

```bash
python piper_test.py --interactive
```

The initial model, speaker, speed, and output filename can be supplied at startup:

```bash
python piper_test.py --interactive --model 1 --speaker 23 --speed fast --output session.wav
```

Interactive mode:

1. prompts with `piper>`;
2. accepts text directly and synthesizes it;
3. saves the WAV file;
4. plays it through `paplay`, `aplay`, or `ffplay` when available; and
5. keeps running so text and settings can be changed again.

Example session:

```text
piper> Hello, this is Piper.
Saved: session.wav

piper> /speed slow
Speed updated: slow (length_scale=1.25)

piper> /speaker 900
Speaker updated: 900

piper> Please read this sentence more slowly.
Saved: session.wav

piper> /output alternate.wav
Output updated: alternate.wav

piper> /status
piper> /quit
```

### Interactive Commands

| Command | Action |
|---|---|
| `<text>` | Synthesize and play entered text |
| `/speed <value>` | Set `slow`, `normal`, `fast`, or a numeric scale from `0.5` to `2.0` |
| `/speaker <id>` | Set a LibriTTS speaker ID from `0` through `903` |
| `/model <index>` | Load another `ENG_MODEL` entry |
| `/output <filename>` | Change the WAV destination |
| `/status` | Display the current model, speaker, speed, and output |
| `/help` | Display the command summary |
| `/quit` or `/exit` | Leave interactive mode |

The Lessac model at `ENG_MODEL[0]` is a single-speaker model. Selecting `/speaker` while it is active uses speaker `0`. Speaker validation is restored when switching to the LibriTTS model.

Use `--no-play` to synthesize without automatically opening an audio player:

```bash
python piper_test.py --interactive --no-play
```

Use Ctrl+C or EOF to leave the interactive prompt.

## Speaker Preview Mode

Audition representative voices before choosing a speaker. All previews use the same text and speed, so differences come primarily from the speaker.

### Command-Line Preview

```bash
python piper_test.py --preview --preview-count 5
```

The LibriTTS model samples evenly across speaker IDs `0` through `903`. The default count is `5`, and valid counts range from `1` through `20`.

Disable playback while generating the preview samples:

```bash
python piper_test.py --preview --preview-count 3 --no-play
```

### Interactive Preview

```text
piper> /preview
piper> /preview 7
```

`/preview` samples five speakers. `/preview 7` samples seven evenly spaced speakers. The preview files are temporary and are deleted after playback.

After auditioning, select a voice:

```text
piper> /speaker 452
```

For the Lessac single-speaker model (`ENG_MODEL[0]`), preview mode uses only speaker `0`.

## Reliable Long-Text and Source Mode

Long input is split at paragraph, sentence, or word boundaries instead of passed to Piper as one large synthesis call. Piper synthesizes every chunk, and the chunks are combined into one complete WAV file.

Example with a source file:

```bash
python piper_test.py --source /path/to/document.txt --save --save-dir transcripts --title chapter-one --chunk-size 900
```

Use `--chunk-size` with values from `100` through `1500`. Smaller values are more conservative for very large documents; `900` is the default.

When `--save` is enabled, each run creates a unique folder such as:

```text
transcripts/chapter-one-20261122-213819/
├── transcript.txt
├── manifest.txt
├── output.wav
├── chunk-0001.wav
├── chunk-0002.wav
└── chunk-0003.wav
```

The folder contains:

- `transcript.txt`: the complete original text;
- `chunk-0001.wav`, `chunk-0002.wav`, and later files: every individual synthesized segment;
- `output.wav`: every chunk combined into one continuous recording;
- `manifest.txt`: title, chunk count, speaker, speed, and output filename.

Without `--save`, a complete combined WAV is still created, but numbered chunks and the transcript folder are not retained.

### Interactive Source and Storage Commands

```text
piper> /source /path/to/document.txt
piper> /save on
piper> /title chapter-one
piper> /source /path/to/document.txt
piper> /save off
```

`/source <file>` loads a UTF-8 text file and synthesizes it while preserving model, speaker, speed, output, and save settings.

`/save on` enables the unique transcript folder for subsequent text and source synthesis. `/save off` disables artifact folders.

`/title <name>` changes the name prefix used for the next transcript folder.

`/chunk` is not currently an interactive command. Use `--chunk-size` at startup for the session.

### Command History

Interactive mode uses prompt-toolkit command history:

- press the **Up Arrow** to recall an earlier command;
- press the **Down Arrow** to move forward in history;
- history is retained while the interactive session remains running;
- text input and slash commands are both included.
