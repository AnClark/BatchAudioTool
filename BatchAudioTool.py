#!/usr/bin/env python3
"""
Batch audio converter / trimmer / normalizer

Copyright (C) AnClark Liu 2025-present.
License: MIT
———————————————————————————————————————————
Usage:
    python audio_tool.py ~/Music -o ~/Processed -t -n -j 4
"""

import sys
import logging
import warnings
from pathlib import Path
from functools import partial
from multiprocessing import Pool, cpu_count

import click
import soundfile as sf
import librosa
import pyloudnorm as pyln
from tqdm import tqdm

warnings.filterwarnings("ignore", category=UserWarning)  # Suppress librosa noise


# ---------- Journal ---------- #
def init_logger(debug: bool):
    level = logging.DEBUG if debug else logging.INFO
    fmt = "%(asctime)s | %(levelname)s | %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")
    if debug:
        fh = logging.FileHandler("audio_tool.debug.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(fh)


# ---------- Utils ---------- #
def collect_audio_files(input_path: Path, recursive: bool = True):
    """Return a list of all supported files in input_path"""
    exts = ("*.wav", "*.flac", "*.mp3", "*.ogg", "*.m4a", "*.aiff", "*.wma")
    files = []
    for ext in exts:
        pattern = "**/" + ext if recursive else ext
        files.extend(input_path.glob(pattern))
    return sorted(files)


def build_output_path(in_file: Path, out_dir: Path, base_dir: Path) -> Path:
    """Consist directory structure, or unify output dir"""
    rel = in_file.relative_to(base_dir)
    out = out_dir / rel.with_suffix(".wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


# ---------- Core routine ---------- #
def process_one(
    args,
    in_file: Path,
    base_dir: Path,
):
    """The full routine of processing ONE file"""
    try:
        out_file = build_output_path(in_file, args["output_dir"], base_dir)

        # 1) Read audio file
        y, sr_native = librosa.load(in_file, sr=None, mono=False)    # "sr" means sample rate
        # Multichannel -> Stereo (or keep as-is)
        if y.ndim > 1 and y.shape[0] == 2:
            y = y.T  # (samples, channels) Intent for processing easily later
        target_sr = args["sample_rate"]
        bit_depth = args["bit_depth"]

        # 2) Resample
        if sr_native != target_sr:
            y = librosa.resample(y, orig_sr=sr_native, target_sr=target_sr)

        # 3) Trim silence
        if args["trim_silence"]:
            top_db = args["silence_thresh"]   # Threshold of silence (in dB)
            frame_length = int(0.1 * target_sr)
            hop_length = frame_length // 4
            y, _ = librosa.effects.trim(
                y, top_db=top_db, frame_length=frame_length, hop_length=hop_length
            )

        # 4) Loudness normalization (via pyln)
        if args["normalize"]:
            meter = pyln.Meter(target_sr)
            # Multichannel support
            loudness = meter.integrated_loudness(y)    # aka. LUFS-I
            y = pyln.normalize.loudness(y, loudness, args["target_lufs"])

        # 5) Bit-depth quantizer
        if bit_depth == 16:
            subtype = "PCM_16"
        elif bit_depth == 24:
            subtype = "PCM_24"
        else:  # 32
            subtype = "PCM_32"

        # Write output file
        sf.write(out_file, y, target_sr, subtype=subtype)
        return None
    except Exception as exc:
        return str(in_file), str(exc)


# ---------- CLI ---------- #
# CLI is powered by Click.
@click.command(help="Batch convert / trim / normalize audio files.")
@click.argument("input_path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(file_okay=False, writable=True, path_type=Path),
              help="Output directory (mirrors input structure if not given)")
@click.option("-r", "--sample-rate", default=44100, type=int, help="Target sample rate [default: 44100]")
@click.option("-b", "--bit-depth", type=click.Choice(["16", "24", "32"]), default="16",
              help="Target bit depth [default: 16]")
@click.option("-t", "--trim-silence", is_flag=True, help="Trim leading/trailing silence")
@click.option("-n", "--normalize", is_flag=True, help="Normalize loudness to target LUFS")
@click.option("--target-lufs", default=-12.0, type=float, help="Target loudness in LUFS [default: -12.0]")
@click.option("--silence-thresh", default=60.0, type=float,
              help="Silence threshold in dB for trimming [default: 60]")
@click.option("-j", "--jobs", default=1, type=int,
              help="Parallel workers (>=2 enables multiprocessing) [default: 1]")
@click.option("--debug", is_flag=True, help="Write debug log to audio_tool.debug.log")
def main(input_path, output_dir, sample_rate, bit_depth, trim_silence, normalize,
         target_lufs, silence_thresh, jobs, debug):
    init_logger(debug)

    # Determine input type: File or Directory
    if input_path.is_file():
        files = [input_path]
        base_dir = input_path.parent
    else:
        files = collect_audio_files(input_path)
        base_dir = input_path

    if not files:
        click.echo("No supported audio files found.", err=True)
        sys.exit(1)

    # Output directory
    if output_dir is None:
        output_dir = base_dir / "processed_audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Pack up parameters
    args = dict(
        output_dir=output_dir,
        sample_rate=sample_rate,
        bit_depth=int(bit_depth),
        trim_silence=trim_silence,
        normalize=normalize,
        target_lufs=target_lufs,
        silence_thresh=silence_thresh,
    )

    # Gather progress and errors
    errors = []

    def _callback(ret):
        if ret:  # Exception found
            errors.append(ret)

    # Parallel or serial processing
    # Parall processing is powered by Process Pool utility.
    if jobs >= 2:
        jobs = min(jobs, cpu_count())
        worker = partial(process_one, args)
        with Pool(processes=jobs) as pool:
            # Show process bar via tqdm
            for ret in tqdm(pool.imap_unordered(worker, files), total=len(files),
                            desc="Processing", unit="file", colour="green"):
                _callback(ret)
    else:
        for f in tqdm(files, desc="Processing", unit="file", colour="green"):
            ret = process_one(args, f, base_dir)
            _callback(ret)

    # Report
    if errors:
        click.echo(f"\nFinished with {len(errors)} error(s):", err=True)
        for fname, err in errors:
            click.echo(f"  - {fname}: {err}", err=True)
    else:
        click.echo("\nAll files processed successfully!")

    logging.shutdown()


if __name__ == "__main__":
    main()
