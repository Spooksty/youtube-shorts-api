import random
import subprocess
from pathlib import Path

from app.integrations.base import WordTiming
from app.media_utils import ffprobe
from app.workflow.context import PipelineError

WIDTH, HEIGHT = 1080, 1920
MAX_DURATION = 60
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
FPS = 30
FADE = 0.4

# E = eased progress of the shot (0..1)
MOTIONS = {
    "zoom_in": ("1+0.18*E", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "zoom_out": ("1.18-0.18*E", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "pan_left": ("1.2", "(iw-iw/zoom)*E", "ih/2-(ih/zoom/2)"),
    "pan_right": ("1.2", "(iw-iw/zoom)*(1-E)", "ih/2-(ih/zoom/2)"),
    "pan_up": ("1.2", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*(1-E)"),
    "pan_down": ("1.2", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*E"),
    "push_corner": ("1+0.22*E", "(iw-iw/zoom)*0.35", "(ih-ih/zoom)*0.35"),
}

ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,84,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,80,80,560,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def group_words(timings: list[WordTiming], max_words: int = 3) -> list[list[WordTiming]]:
    groups, current = [], []
    for t in timings:
        current.append(t)
        if len(current) >= max_words or t.word[-1] in ".!?,":
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def build_subtitles(timings: list[WordTiming], path: Path):
    lines = [ASS_HEADER]
    for g in group_words(timings):
        text = " ".join(w.word for w in g).replace("{", "").replace("}", "")
        lines.append(f"Dialogue: 0,{ass_time(g[0].start)},{ass_time(g[-1].end)},Default,,0,0,0,,{text}\n")
    path.write_text("".join(lines), encoding="utf-8")


def run_ffmpeg(args: list[str], cwd: Path):
    proc = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise PipelineError(f"FFmpeg kļūda: {proc.stderr.strip()[-400:]}")


def pick_motions(count: int) -> list[str]:
    names, picked = list(MOTIONS), []
    for _ in range(count):
        options = [n for n in names if not picked or n != picked[-1]]
        picked.append(random.choice(options))
    return picked


def motion_filter(name: str, frames: int) -> str:
    z, x, y = MOTIONS[name]
    p = f"(on/{frames})"
    eased = f"({p}*{p}*(3-2*{p}))"
    z, x, y = (e.replace("E", eased) for e in (z, x, y))
    # 2x canvas, otherwise slow pans jitter
    w2, h2 = WIDTH * 2, HEIGHT * 2
    return (f"scale={w2}:{h2}:force_original_aspect_ratio=increase:out_range=tv,crop={w2}:{h2},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
            "setsar=1,format=yuv420p")


def assemble(folder: Path, clips: list[Path], audio: Path, duration: float) -> Path:
    n = len(clips)
    fade = FADE if n > 1 else 0
    seg_len = (duration + fade * (n - 1)) / n + 0.3
    frames = int(seg_len * FPS)
    video_vf = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:out_range=tv,crop={WIDTH}:{HEIGHT},"
                f"fps={FPS},setsar=1,format=yuv420p")

    segments = []
    for i, (clip, motion) in enumerate(zip(clips, pick_motions(n)), 1):
        seg = f"seg_{i}.mp4"
        if clip.suffix.lower() in IMAGE_SUFFIXES:
            run_ffmpeg(["-i", clip.name, "-vf", motion_filter(motion, frames), "-frames:v", str(frames),
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", seg], folder)
        else:
            run_ffmpeg(["-stream_loop", "-1", "-i", clip.name, "-frames:v", str(frames), "-vf", video_vf, "-an",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", seg], folder)
        segments.append(seg)

    inputs = [arg for seg in segments for arg in ("-i", seg)]
    chain, last = [], "[0:v]"
    for k in range(1, n):
        offset = k * (frames / FPS - fade)
        chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={fade}:offset={offset:.3f}[x{k}]")
        last = f"[x{k}]"
    # ass filter gives yuv444p, browsers won't play that
    chain.append(f"{last}ass=subtitles.ass,format=yuv420p[v]")

    run_ffmpeg([*inputs, "-i", audio.name, "-filter_complex", ";".join(chain),
                "-map", "[v]", "-map", f"{n}:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-color_range", "tv",
                "-profile:v", "high",
                "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", "final.mp4"], folder)

    for name in segments:
        (folder / name).unlink(missing_ok=True)
    return folder / "final.mp4"


def technical_check(path: Path) -> dict:
    info = ffprobe(path)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    duration = float(info["format"]["duration"])
    width, height = (video["width"], video["height"]) if video else (0, 0)

    problems = []
    if duration > MAX_DURATION:
        problems.append(f"ilgums {duration:.1f} s > {MAX_DURATION} s")
    if (width, height) != (WIDTH, HEIGHT):
        problems.append(f"izšķirtspēja {width}×{height}")
    if not has_audio:
        problems.append("nav audio celiņa")

    return {"duration": duration, "width": width, "height": height, "has_audio": has_audio,
            "passed": not problems, "problems": problems}
