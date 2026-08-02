import base64
import os
import subprocess
import tempfile

from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.environ.get("USE_MOCK", "true").lower() == "true"

MAX_VIDEO_SECONDS = 30
FRAMES_PER_VIDEO = 3


class UploadError(Exception):
    """A file failed validation (size/duration) or processing (ffmpeg/API)."""


def describe_image(path: str) -> str:
    if USE_MOCK:
        return f"Mock visual description of {os.path.basename(path)}: bold colors, urban setting, energetic mood."

    from openai import OpenAI

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lstrip(".").lower() or "png"

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image's visual style, mood, and any brand-relevant "
                        "details (colors, composition, subject matter) in 2-3 sentences.",
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
                ],
            }
        ],
    )
    return response.choices[0].message.content or ""


def _video_duration_seconds(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def extract_video_frames(path: str, n: int = FRAMES_PER_VIDEO) -> list[str]:
    duration = _video_duration_seconds(path)
    if duration > MAX_VIDEO_SECONDS:
        raise UploadError(
            f"{os.path.basename(path)} is {duration:.0f}s long — videos must be "
            f"{MAX_VIDEO_SECONDS}s or shorter."
        )

    frame_paths = []
    tmpdir = tempfile.mkdtemp(prefix="video_frames_")
    for i in range(n):
        timestamp = duration * (i + 1) / (n + 1)
        frame_path = os.path.join(tmpdir, f"frame_{i}.jpg")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(timestamp), "-i", path, "-frames:v", "1", frame_path],
                capture_output=True, check=True,
            )
        except subprocess.CalledProcessError as e:
            raise UploadError(f"Could not extract frames from {os.path.basename(path)}: {e}")
        frame_paths.append(frame_path)
    return frame_paths


def describe_video(path: str) -> str:
    if USE_MOCK:
        return f"Mock video description of {os.path.basename(path)}: handheld motion, quick cuts, high energy."

    frames = extract_video_frames(path)
    descriptions = [describe_image(frame) for frame in frames]
    return " ".join(f"[frame {i + 1}] {d}" for i, d in enumerate(descriptions))


def generate_image(prompt: str) -> str | None:
    """Returns a local filepath to the generated image, or None if generation failed."""
    if USE_MOCK:
        return None

    from openai import OpenAI

    try:
        client = OpenAI()
        result = client.images.generate(model="gpt-image-1", prompt=prompt, size="1024x1024", n=1)
        image_bytes = base64.b64decode(result.data[0].b64_json)
    except Exception:
        return None

    fd, path = tempfile.mkstemp(suffix=".png", prefix="reference_image_")
    with os.fdopen(fd, "wb") as f:
        f.write(image_bytes)
    return path
