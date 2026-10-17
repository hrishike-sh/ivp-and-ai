"""Loopback-only Traffic Lab API and static web application. No cloud dependencies."""
import argparse
import csv
import hashlib
import json
import math
import mimetypes
import re
import secrets
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ivp.downloads import FileServer
from ivp.inspection import inspect_region
from ivp.jobs import ROOT, cancel_job, history, job_lock, new_run, now, refreshed_status, start_video
from ivp.media import load_image, png_bytes, preview_frame, probe_video, write_json, source_revision
from ivp.pipeline import PRESETS, Settings, histogram, process_frame
from ivp.workspace import run_details, source_name
from ivp.automatic import choose_settings
from ivp.stages import build_stages, manifest
from ivp.survey import survey

WEB = ROOT / "web"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
SAMPLE_NAMES = {"indian_riders.png": "Indian motorcycles", "indian_night.png": "Indian night traffic",
                'indian-motion.mp4': 'Indian traffic · crowded stress test', 'traffic-motion.avi': 'Pedestrian movement · OpenCV sample',
                'india-city.mp4': 'Indian city traffic - recommended automatic tracking demo',
                'india-delhi-overhead.mp4': 'Delhi junction - crowded autos, buses & bikes',
                'india-intersection.mp4': 'Delhi intersection - mixed street traffic', 'india-rickshaws.mp4': 'Delhi street - rickshaws & close occlusion',
                'highway-motion.mp4': 'Highway traffic · fixed camera demo',
                "street.jpg": "Street scene", "low_light.png": "Low light · simulated", "noisy.png": "Sensor noise · simulated",
                "crossing.jpg": "Zebra crossing", "sample_video.mp4": "Video · still image + test audio"}
DOWNLOADS = {"processed.png": "Processed image", "processed.mp4": "Processed video", "detections.png": "Detected objects",
             'motion-incidents.jsonl': 'Incident assessments (JSONL)', 'motion-incidents.csv': 'Incident assessments (CSV)',
             'motion-incidents.json': 'Incident review summary and configuration',
             'motion-tracks.png': 'Full-resolution tracks and speed', 'motion-flow.png': 'Local optical-flow arrows',
             'motion-evidence.zip': 'Motion analysis evidence package', 'motion-heatmap.png': 'Movement heatmap',
             'motion-mosaic.png': 'Peak activity comparison', 'motion-activity.csv': 'Motion timeline (CSV)',
             'motion-crossings.csv': 'Line crossings (CSV)', 'motion-tracks.csv': 'Track trajectories (CSV)',
             'motion-background.png': 'Estimated background', 'motion-raw-foreground.png': 'Raw foreground labels',
             'motion-shadows.png': 'Rejected shadow mask', 'motion-mask.png': 'Cleaned foreground mask',
             'survey-evidence.zip': 'Survey images and masks', 'fragments.csv': 'Fragment measurements (CSV)',
             'annotated-survey.png': 'Annotated marking survey',
             'processing-policy.json': 'Automatic processing policy',
             "ivp-stages.zip": "All IVP stages + explanations",
             "report.json": "Settings & measurements", "masks.zip": "Feature masks", "measurements.csv": "Frame measurements",
             "scene_changes.csv": "Scene changes", "coordinates.json": "Coordinate mapping", "events.jsonl": "AI events",
             "detections.jsonl": "AI frame decisions", "evidence.zip": "Event evidence", "scene_features.zip": "Scene features"}


def parse_settings(value):
    if not isinstance(value, dict) or set(value) - set(Settings.__dataclass_fields__):
        raise ValueError("Unknown processing settings.")
    defaults = Settings().to_dict()
    for name, item in value.items():
        expected = type(defaults[name])
        if expected in (int, float):
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                raise ValueError(f"{name} must be a finite number.")
            if expected is int and type(item) is not int:
                raise ValueError(f"{name} must be an integer.")
        elif type(item) is not expected:
            raise ValueError(f"Invalid type for {name}.")
    settings = Settings(**value)
    if settings.max_width not in (0,) and not 2 <= settings.max_width <= 8192:
        raise ValueError("Maximum width must be 0 or between 2 and 8192.")
    if settings.line_length > 8192:
        raise ValueError("Line length is too large.")
    return settings


class Lab:
    def __init__(self):
        self.files = FileServer()
        self.media = {}
        self.lock = threading.Lock()
        self.cache = None
        self.auto_profiles = {}

        self.executor = ThreadPoolExecutor(max_workers=1)
        self.review_future = None
        self.review_id = None
        self.token = secrets.token_urlsafe(32)

    def close(self):
        self.files.close()
        self.executor.shutdown(wait=False, cancel_futures=True)

    def register(self, path):
        path = Path(path)
        info = probe_video(path) if path.suffix.lower() in (".mp4", ".mov", ".avi") else None
        if info is None:
            rgb = load_image(path)
            info = {"kind": "image", "width": rgb.shape[1], "height": rgb.shape[0]}
        key = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:24]
        info['source_revision'] = source_revision(path)
        registry = ROOT / "temp" / "webmedia"
        registry.mkdir(parents=True, exist_ok=True)
        write_json(registry / (key + ".json"), {"path": str(path.resolve())})
        self.media[key] = (path, info)
        self.cache = None
        return {"id": key, "name": path.name, "size_bytes": path.stat().st_size, **info}

    def resume(self, key):
        if not isinstance(key, str) or len(key) != 24 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError("Previous footage is unavailable; choose a file again.")
        record = ROOT / "temp" / "webmedia" / (key + ".json")
        try:
            path = Path(json.loads(record.read_text())["path"]).resolve()
            if not any(path.is_relative_to((ROOT / folder).resolve()) for folder in ("uploads", "demo")):
                raise ValueError("Saved source is outside the media folders.")
            if hashlib.sha256(str(path).encode()).hexdigest()[:24] != key:
                raise ValueError("Saved source identity changed.")
            return self.register(path)
        except (OSError, KeyError, TypeError) as exc:
            raise ValueError("Previous footage is unavailable; choose a file again.") from exc

    def frame(self, data):
        if data.get("media") not in self.media:
            raise ValueError("Choose a sample or upload your footage again.")
        path, info = self.media[data["media"]]
        stamp = data.get("timestamp", 0)
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp) or stamp < 0:
            raise ValueError("Invalid frame timestamp.")
        if info["kind"] == "video":
            stamp = min(stamp, max(0, info["duration"] - .001))
            rgb, stamp = preview_frame(path, info, stamp)
        else:
            rgb, stamp = load_image(path), 0.
        return path, info, rgb, stamp

    def processed(self, data):
        settings, _ = self.resolve_settings(data)
        key = (data.get("media"), data.get("timestamp", 0), settings)
        if self.cache and self.cache[0] == key:
            return self.cache[1]
        path, info, rgb, stamp = self.frame(data)
        result = process_frame(rgb, settings, stamp)
        value = path, info, result, settings
        self.cache = key, value
        return value

    def resolve_settings(self, data):
        mode = data.get('mode', 'manual')
        if mode not in ('automatic', 'manual'):
            raise ValueError('Unknown processing mode.')
        if mode == 'manual':
            return parse_settings(data.get('settings', {})), {'mode': 'manual'}
        key = data.get('media')
        if key not in self.media:
            raise ValueError('Choose footage first.')
        if key not in self.auto_profiles:
            _, info, rgb, stamp = self.frame({**data, 'timestamp': 0})
            settings, explanation = choose_settings(rgb)
            self.auto_profiles[key] = settings, {**explanation, 'mode': 'automatic',
                'reference_timestamp': stamp,
                'scope': 'Fixed settings from the first frame for the whole video.' if info['kind'] == 'video' else 'Settings selected from this image.'}
        return self.auto_profiles[key]

    def preview(self, data):
        path, info, result, settings = self.processed(data)
        folder = ROOT / "temp" / "webpreviews" / data["media"]
        folder.mkdir(parents=True, exist_ok=True)
        version = secrets.token_hex(6)
        def asset(name, pixels):
            target = folder / (name + ".png")
            target.write_bytes(png_bytes(pixels))
            return self.files.url(target) + "?v=" + version
        before = result.stages["Prepared"]
        graph = build_stages(result, settings)
        steps = manifest(graph)
        for step, entry in zip(steps, graph):
            step['url'] = asset('ivp-' + step['id'], entry['image'])
            step['download'] = self.files.url(folder / ('ivp-' + step['id'] + '.png'), True)
        return {"name": path.name, "timestamp": result.timestamp, "settings": settings.to_dict(),
                "source_size": result.source_size, "size": [result.color_rgb.shape[1], result.color_rgb.shape[0]],
                "original": asset("original", before), "processed": asset("processed", result.color_rgb),
                "features": {name: asset(f"feature-{i}", pixels) for i, (name, pixels) in enumerate(result.features.items())},
                "stages": {name: asset(f"stage-{i}", pixels) for i, (name, pixels) in enumerate(result.stages.items())},
                "measurements": result.measurements, "candidates": result.candidates,
                "histograms": {"original": histogram(before), "processed": histogram(result.color_rgb)},
                "mapping": result.transform_to_source.tolist(), 'ivp_steps': steps,
                'automatic': self.resolve_settings(data)[1]}

    def marking_survey(self, data):
        # Always measure original colour at a fixed resolution; enhancement
        # sliders must not manufacture paint coverage or change its geometry.
        path, info, rgb, stamp = self.frame(data)
        settings = Settings(max_width=1280)
        prepared = process_frame(rgb, settings, stamp)
        report, images = survey(prepared.stages['Prepared'], data.get('rectangle'), prepared.transform_to_source)
        report.update({'source': path.name, 'kind': 'ivp_marking_survey', 'timestamp_seconds': stamp,
                       'created_at': now(), 'source_size': prepared.source_size,
                       'settings': settings.to_dict()})
        run = new_run()
        write_json(run / 'report.json', report)
        (run / 'annotated-survey.png').write_bytes(png_bytes(images['annotated-survey']))
        fields = ['id', 'area_px', 'bbox_x', 'bbox_y', 'bbox_width_px', 'bbox_height_px',
                  'long_side_px', 'short_side_px', 'orientation_deg_clockwise_from_right',
                  'touches_roi_boundary', 'source_centre_x', 'source_centre_y']
        with (run / 'fragments.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(report['fragments'])
        with zipfile.ZipFile(run / 'survey-evidence.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, pixels in images.items():
                archive.writestr(name + '.png', png_bytes(pixels))
            archive.write(run / 'report.json', 'report.json')
            archive.write(run / 'fragments.csv', 'fragments.csv')
        write_json(run / 'status.json', {'state': 'complete', 'progress': 1,
                   'message': 'IVP marking survey ready.', 'updated_at': now()})
        return self.run(run.name)

    def export(self, data):
        path, info, result, settings = self.processed(data)
        masks = data.get("masks", [])
        if not isinstance(masks, list) or any(name not in result.features for name in masks):
            raise ValueError("Unknown feature mask.")
        run = new_run()
        (run / "processed.png").write_bytes(png_bytes(result.color_rgb))
        with zipfile.ZipFile(run / "masks.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for name in masks:
                archive.writestr(name.replace(" ", "_") + ".png", png_bytes(result.features[name]))
        graph = build_stages(result, settings)
        with zipfile.ZipFile(run / 'ivp-stages.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for i, step in enumerate(graph):
                archive.writestr(f"{i+1:02d}-{step['id']}.png", png_bytes(step['image']))
            archive.writestr('stages.json', json.dumps(manifest(graph), indent=2))
            archive.writestr('processing.json', json.dumps({'source': path.name,
                'timestamp': result.timestamp, 'settings': settings.to_dict(),
                'policy': self.resolve_settings(data)[1],
                'transform_to_source_pixel_centres': result.transform_to_source.tolist()}, indent=2))
        write_json(run / "report.json", {"schema_version": 1, "source": path.name,
                   "kind": "video_frame" if info["kind"] == "video" else "image", "created_at": now(),
                   "timestamp_seconds": result.timestamp, "settings": settings.to_dict(),
                   "measurements": result.measurements, "candidates": result.candidates,
                   'ivp_stages': manifest(graph), 'processing_policy': self.resolve_settings(data)[1],
                   "source_size": result.source_size, "processed_size": [result.color_rgb.shape[1], result.color_rgb.shape[0]],
                   "transform_to_source_pixel_centres": result.transform_to_source.tolist(), "selected_masks": masks})
        write_json(run / "status.json", {"state": "complete", "progress": 1, "message": "Image export ready.", "updated_at": now()})
        return self.run(run.name)

    def run(self, name):
        if not isinstance(name, str) or not name or Path(name).name != name or "/" in name or "\\" in name or name in (".", ".."):
            raise ValueError("Invalid run identifier.")
        run = ROOT / "runs" / name
        if not (run / "status.json").is_file():
            raise ValueError("Saved run was not found.")
        details = run_details(run)
        links = [{"name": file, "label": label, "url": self.files.url(run / file, True)} for file, label in DOWNLOADS.items() if (run / file).is_file()]
        status = refreshed_status(run)
        if status.get("state") != "complete":
            links = []
        preview = None
        if status.get("state") == "complete":
            incident_summary = details.get('motion',{}).get('incidents',{})
            for event in incident_summary.get('events',[]):
                thumbnail = event.get('thumbnail')
                if (isinstance(thumbnail,str) and re.fullmatch(r'incident-\d{6}\.png',thumbnail)
                        and (run/thumbnail).is_file()):
                    event['thumbnail_url'] = self.files.url(run/thumbnail)
            for file in ("processed.mp4", "detections.png", "processed.png", "annotated-survey.png"):
                if (run / file).exists():
                    preview = {"url": self.files.url(run / file), "video": file.endswith(".mp4"), "name": file}
                    break
        return {"id": name, "source": source_name(details), "status": status, "downloads": links, "preview": preview, "report": details}

    def post(self, route, data):
        if route == '/api/motion':
            from ivp.motion import MotionAnalyzer
            if data.get('media') not in self.media:
                raise ValueError('Choose a traffic video first.')
            path, info = self.media[data['media']]
            if info['kind'] != 'video':
                raise ValueError('Motion analysis needs a video. Choose the Indian traffic moving-video sample.')
            if info.get('source_revision') != source_revision(path):
                raise ValueError('This video changed since it was opened. Reopen it and mark the road calibration again.')
            calibration = data.get('calibration')
            if calibration is not None:
                if (not isinstance(calibration, dict) or
                        calibration.get('media_id') != data['media'] or
                        calibration.get('source_revision') != info['source_revision'] or
                        calibration.get('reference_frame') != 0):
                    raise ValueError('Calibration belongs to different or outdated footage. Mark four road corners on this video first.')
            config = {'axis': data.get('axis','horizontal'), 'position': data.get('position',.65),
                      'rectangle': data.get('rectangle'), 'calibration': data.get('calibration'),
                      'target_rectangle':data.get('target_rectangle'), 'tracking_mode':data.get('tracking_mode','ivp'),
                      'output_view':data.get('output_view','tracks')}
            MotionAnalyzer(**config)
            from ivp.incidents import validate_config
            incidents = validate_config(data.get('incidents'))
            if incidents and incidents['enabled']:
                if config['tracking_mode'] != 'vehicles':
                    raise ValueError('Incident review needs automatic vehicle tracking. Select Vehicles · local detector + IVP.')
                config['incidents'] = incidents
            return self.run(start_video(path,info,Settings(max_width=960),[],motion=config).name)
        if route == '/api/survey':
            return self.marking_survey(data)
        if route == "/api/validate-settings":
            return parse_settings(data.get("settings", {})).to_dict()
        if route == "/api/sample":
            name = data.get("name")
            if name not in SAMPLE_NAMES or not (ROOT / "demo" / name).is_file():
                raise ValueError("Sample not found.")
            return self.register(ROOT / "demo" / name)
        if route == "/api/preview":
            return self.preview(data)
        if route == "/api/region":
            return inspect_region(self.processed(data)[2], data.get("rectangle"))
        if route == "/api/export":
            return self.export(data)
        if route == "/api/job":
            # Validate without running expensive IVP before starting the worker.
            if data.get("media") not in self.media:
                raise ValueError("Choose footage first.")
            path, info = self.media[data["media"]]
            ai = data.get("ai", False)
            if type(ai) is not bool or (not ai and info["kind"] != "video"):
                raise ValueError("Use image export for still images.")
            settings, policy = self.resolve_settings(data)
            masks = data.get("masks", [])
            if not isinstance(masks, list) or any(not isinstance(v, str) for v in masks):
                raise ValueError("Invalid masks.")
            allowed_masks = {"Grayscale", "Hue", "Saturation", "Value", "Colour mask", "White marking mask", "Edges", "Threshold", "Morphology", "Contours", "Lines", "Road candidates", "Stripe mask", "Sobel magnitude", "Laplacian", "Morphological gradient", "Top hat", "Black hat"}
            if any(v not in allowed_masks for v in masks):
                raise ValueError("Unknown feature mask.")
            run = start_video(path, info, settings, masks, ai=ai)
            write_json(run / 'processing-policy.json', policy)
            return self.run(run.name)
        if route == "/api/cancel":
            run = self.run(data.get("id"))
            if run["status"]["state"] in ("queued", "running", "encoding"):
                cancel_job(ROOT / "runs" / run["id"])
            return {"message": "Cancellation requested."}
        if route == "/api/review":
            if self.review_future and not self.review_future.done():
                raise RuntimeError("A scene review is already running.")
            _, _, rgb, stamp = self.frame(data)
            def review():
                from traffic_ai.local_vision import review_frame
                with job_lock():
                    return review_frame(rgb, stamp)
            self.review_id = secrets.token_hex(12)
            self.review_future = self.executor.submit(review)
            return {"id": self.review_id, "state": "running"}
        raise ValueError("Unknown operation.")


def create_server(port=8511):
    lab = Lab()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def permitted(self):
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if host not in allowed:
                self.respond({'error': 'Localhost access only.'}, 403)
                return False
            return True

        def respond(self, value, status=200):
            if status >= 400 and self.command == 'POST' and not getattr(self, 'body_started', False):
                # On Windows, closing with unread request bytes can reset the
                # connection before the client receives this actionable error.
                # Drain only small rejected bodies, with a short bounded wait.
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    length = 0
                if 0 < length <= 65536:
                    previous_timeout = self.connection.gettimeout()
                    try:
                        self.connection.settimeout(.25)
                        self.rfile.read(length)
                    except OSError:
                        pass
                    finally:
                        self.connection.settimeout(previous_timeout)
                self.body_started = True
            payload = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if not self.permitted():
                return
            parsed = urlparse(self.path)
            route, query = parsed.path, parse_qs(parsed.query)
            try:
                if route == "/api/health":
                    return self.respond({"app": "traffic-lab-web", "version": 1})
                if route == "/api/config":
                    from traffic_ai.runtime import runtime_root, python_path
                    vehicle_ready=python_path().is_file() and (runtime_root()/"models"/"yolo11s.pt").is_file()
                    return self.respond({"vehicle_tracking_ready":vehicle_ready,"defaults": Settings().to_dict(), "presets": {k: v.to_dict() for k, v in PRESETS.items()},
                                         "samples": [{"name": k, "label": v} for k, v in SAMPLE_NAMES.items() if (ROOT / "demo" / k).is_file()]})
                if route == "/api/media":
                    with lab.lock:
                        return self.respond(lab.resume(query.get("id", [None])[0]))
                if route == "/api/runs":
                    return self.respond([lab.run(p.parent.name) for p in history()])
                if route == "/api/run":
                    return self.respond(lab.run(query.get("id", [None])[0]))
                if route == "/api/review":
                    if query.get("id", [None])[0] != lab.review_id or lab.review_future is None:
                        raise ValueError("Review not found.")
                    if not lab.review_future.done():
                        return self.respond({"state": "running"})
                    try:
                        return self.respond({"state": "complete", "review": lab.review_future.result()})
                    except Exception as exc:
                        return self.respond({"state": "failed", "error": str(exc)})
                static = {"/": "index.html", "/app.js": "app.js", "/styles.css": "styles.css"}
                if route not in static:
                    return self.respond({"error": "Not found"}, 404)
                path = WEB / static[route]
                body = path.read_bytes().replace(b"__REQUEST_TOKEN__", lab.token.encode())
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' http://127.0.0.1:*; media-src http://127.0.0.1:*; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, OSError) as exc:
                self.respond({"error": str(exc)}, 400)

        def do_POST(self):
            if not self.permitted():
                return
            if self.headers.get("X-Traffic-Token") != lab.token:
                return self.respond({"error": "Reload the app to refresh your session."}, 403)
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
                return self.respond({"error": "Cross-origin request rejected."}, 403)
            if not lab.lock.acquire(blocking=False):
                return self.respond({"error": "Another operation is running. Try again shortly."}, 409)
            try:
                self.connection.settimeout(120)
                parsed = urlparse(self.path)
                length = int(self.headers.get("Content-Length", "0"))
                limit = 1024 ** 3 if parsed.path == "/api/upload" else 65536
                if not 0 < length <= limit:
                    raise ValueError("File is empty or exceeds the 1 GB upload limit." if limit > 65536 else "Invalid request size.")
                if parsed.path == "/api/upload":
                    name = parse_qs(parsed.query).get("name", [""])[0].replace("\\", "/").rsplit("/", 1)[-1]
                    if Path(name).suffix.lower() not in EXTENSIONS or len(name) > 180 or any(c in name for c in '<>:"|?*\x00'):
                        raise ValueError("Choose a JPG, PNG, MP4, MOV or AVI file with a valid filename.")
                    folder = ROOT / "uploads" / secrets.token_hex(12)
                    folder.mkdir(parents=True)
                    path = folder / name
                    self.body_started = True
                    try:
                        with path.open("wb") as output:
                            remaining = length
                            while remaining:
                                chunk = self.rfile.read(min(1024 * 1024, remaining))
                                if not chunk:
                                    raise ValueError("Upload was interrupted; select the file again.")
                                output.write(chunk)
                                remaining -= len(chunk)
                        result = lab.register(path)
                    except Exception:
                        # Only this request's newly created, rejected copy.
                        # Accepted footage and the user's original are untouched.
                        try:
                            path.unlink(missing_ok=True)
                            folder.rmdir()
                        except OSError:
                            import traceback
                            traceback.print_exc()
                        raise
                else:
                    self.body_started = True
                    data = json.loads(self.rfile.read(length))
                    if not isinstance(data, dict):
                        raise ValueError("Expected a JSON object.")
                    result = lab.post(parsed.path, data)
                self.respond(result)
            except (ValueError, TypeError, OSError, RuntimeError) as exc:
                self.respond({"error": str(exc)}, 400)
            except Exception:
                import traceback
                traceback.print_exc()
                self.respond({"error": "Processing failed. See temp/server.log for details."}, 500)
            finally:
                lab.lock.release()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.lab = lab
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8511)
    args = parser.parse_args()
    server = create_server(args.port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        server.lab.close()
