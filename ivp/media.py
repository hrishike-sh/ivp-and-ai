import io
import json
import shutil
import subprocess
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


class MediaError(ValueError):
    pass


def tool_path(name):
    path = shutil.which(name)
    if not path:
        raise MediaError(f"{name} is missing. Install FFmpeg, add its bin folder to PATH, then restart the app.")
    return path


def hidden_process_options():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if hasattr(subprocess, "CREATE_NO_WINDOW") else {}


def probe_video(path):
    command = [tool_path("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, **hidden_process_options())
        if result.returncode:
            raise MediaError("Cannot decode this video. Try exporting it as an H.264 MP4. " + result.stderr[-400:])
        info = json.loads(result.stdout)
        stream = next((s for s in info["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")), None)
        if not stream:
            raise MediaError("The selected file does not contain a video stream.")
        rotation = float(stream.get("tags", {}).get("rotate", 0))
        for side in stream.get("side_data_list", []):
            if "rotation" in side:
                rotation = float(side["rotation"])
        rate = stream.get("avg_frame_rate", "0/1")
        num, den = map(float, rate.split("/"))
        fps = num / den if den else 0
        width, height = stream["width"], stream["height"]
        if round(rotation / 90) % 2:
            width, height = height, width
        duration = float(stream.get("duration") or info.get("format", {}).get("duration") or 0)
        return {"kind": "video", "width": width, "height": height, "encoded_width": stream["width"],
                "encoded_height": stream["height"], "duration": duration, "fps": fps,
                "rotation": rotation, "stream_index": stream["index"],
                "frame_count": int(stream.get("nb_frames", 0) or 0),
                "has_audio": any(s["codec_type"] == "audio" for s in info["streams"]),
                "codec": stream.get("codec_name", "unknown"), "size_bytes": Path(path).stat().st_size}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, OSError) as exc:
        raise MediaError(f"Could not inspect video: {exc}") from exc


def load_image(path):
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                layer = image.convert("RGBA")
                background = Image.new("RGBA", layer.size, "white")
                image = Image.alpha_composite(background, layer)
            rgb = np.asarray(image.convert("RGB")).copy()
            if min(rgb.shape[:2]) < 2:
                raise MediaError("Image dimensions must be at least 2 × 2 pixels.")
            return rgb
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise MediaError("Cannot read this image. Use a valid JPG or PNG; very large images should be resized first.") from exc


def orient_video(rgb, rotation):
    quarter_turns = round(rotation / 90) % 4
    return np.ascontiguousarray(np.rot90(rgb, quarter_turns)) if quarter_turns else rgb


def video_frames(path, info):
    try:
        with av.open(str(path)) as container:
            stream = container.streams[info["stream_index"]]
            first = None
            last = None
            pending = None
            for frame in container.decode(stream):
                if frame.pts is None:
                    raise MediaError("Video frames have no presentation timestamps. Re-export the source as MP4.")
                absolute = float(frame.pts * frame.time_base)
                if first is None:
                    first = absolute
                stamp = absolute - first
                if last is not None and stamp <= last:
                    raise MediaError("Video has repeated or out-of-order timestamps. Re-export it before processing.")
                if pending is not None:
                    old_frame, old_stamp, old_absolute = pending
                    yield orient_video(old_frame.to_ndarray(format="rgb24"), info["rotation"]), old_stamp, stamp - old_stamp, old_absolute
                last = stamp
                pending = (frame, stamp, absolute)
            if pending is not None:
                frame, stamp, absolute = pending
                duration = float(frame.duration * frame.time_base) if frame.duration else 1 / (info["fps"] or 25)
                yield orient_video(frame.to_ndarray(format="rgb24"), info["rotation"]), stamp, duration, absolute
    except av.FFmpegError as exc:
        raise MediaError(f"Video decoding failed: {exc}. Try converting the source to H.264 MP4.") from exc


def preview_frame(path, info, seconds):
    try:
        with av.open(str(path)) as container:
            stream = container.streams[info["stream_index"]]
            start = stream.start_time or 0
            target = start + int(seconds / stream.time_base)
            if seconds > 0:
                container.seek(target, stream=stream, backward=True)
            last = None
            for frame in container.decode(stream):
                stamp = float((frame.pts - start) * stream.time_base) if frame.pts is not None else 0
                last = (orient_video(frame.to_ndarray(format="rgb24"), info["rotation"]), max(0, stamp))
                if stamp >= seconds:
                    return last
            if last:
                return last
        raise MediaError("No readable frame at this position. Move the slider earlier.")
    except av.FFmpegError as exc:
        raise MediaError(f"Cannot preview this position: {exc}") from exc


def png_bytes(array):
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG")
    return buffer.getvalue()


def write_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
