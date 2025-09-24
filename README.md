# BatchAudioTool

BatchAudioTool is a simple CLI tool to process a bundle of audio files. It aims at production, especially for those siturations which need to process a large number of audio assets (e.g. game development).

**This project requires Python version >= 3.10.**

## Features

- Support major audio formats (WAV, FLAC, MP3, etc.)
- Sample rate conversion
- Bit depth conversion
- Trim leading/trailing silence (useful for game assets / announces)
- Loudness normalization (default -12 LUFS)
- Parallel processing
- Tunable parameters via command line

## Usage

```
Usage: BatchAudioTool.py [OPTIONS] INPUT_PATH

  Batch convert / trim / normalize audio files.

Options:
  -o, --output-dir DIRECTORY  Output directory (mirrors input structure if not
                              given)
  -r, --sample-rate INTEGER   Target sample rate [default: 44100]
  -b, --bit-depth [16|24|32]  Target bit depth [default: 16]
  -t, --trim-silence          Trim leading/trailing silence
  -n, --normalize             Normalize loudness to target LUFS
  --target-lufs FLOAT         Target loudness in LUFS [default: -12.0]
  --silence-thresh FLOAT      Silence threshold in dB for trimming [default:
                              60]
  -j, --jobs INTEGER          Parallel workers (>=2 enables multiprocessing)
                              [default: 1]
  --debug                     Write debug log to audio_tool.debug.log
  --help                      Show this message and exit.
```

Examples:

```bash
# Convert audio files in Audio_In/, targeting 44100Hz, 16-bit by default.
# Output converted files to Audio_Out/.
./BatchAudioTool.py -o Audio_Out/ Audio_In/

# Normalize volume to -10 LUFS
./BatchAudioTool.py -o Audio_Out/ -n 10 Audio_In/
```

## How to install

### Common (Windows, macOS, Ubuntu, etc.)

```bash
# Clone this repo
git clone https://github.com/AnClark/BatchAudioTool.git
cd BatchAudioTool

# Install dependencies
pip install -r requirements.txt

# Test and run this application
./BatchAudioTool.py
```

### Arch Linux

Due to limitations of Arch Linux, you cannot directly use Pip to install packages globally. Virtual environment is recommended.

```bash
# Install virtualenv CLI
sudo pacman -S python-virtualenv

# Clone this repo
git clone https://github.com/AnClark/BatchAudioTool.git
cd BatchAudioTool

# Initialize virtual environment
virtualenv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test and run this application
./BatchAudioTool.py
```

# License

MIT.