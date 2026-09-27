from collections import Counter
from dataclasses import asdict, replace

import cv2

from .contracts import Decision, FrameAnalysis, Rule, Verdict
from .events import EventCollector
from .perception import Perception
from .render import annotate
from .riders import RiderAssociator, associate_riders
from .rules import RuleEngine, SceneEvidence
from .scene import SceneProposer
from .segmentation import CameraStability, RoadSegmenter, mask_polygons
from .markings import grounded_markings
from .signals import signal_observation
from .trajectories import Trajectories
from .arrows import road_arrows
from .geometry import point_in_polygon
from .signs import SignClassifier, sign_candidates
from .approaches import ApproachResolver, infer_approaches
from .turn_signs import TurnSignDetector
from .turn_context import TurnContexts


class Analyzer:
    def __init__(self, status=lambda message: None, cancel=lambda: None):
        self.cancel = cancel
        self.status = status
        self.sign_classifier = None
        self.turn_sign_detector = None
        self.sign_observations = []
        status("Loading road-user and helmet models. First use downloads weights.")
        self.perception = Perception()
        cancel()
        status(f"Loading automatic scene model on {self.perception.device}.")
        self.scene_model = SceneProposer(device=self.perception.device)
        cancel()
        status("Loading road and sidewalk segmentation model.")
        self.segmenter = RoadSegmenter(device="cpu")
        self.camera = CameraStability()
        self.rules = RuleEngine()
        self.rider_associator = RiderAssociator()
        self.trajectories = Trajectories()
        self.turn_contexts = TurnContexts()
        self.turn_observations = []
        self.events = EventCollector()
        self.scene_id = -1
        self.scene = None
        self.scene_dirty = False
        self.scene_proposals = []
        self.scene_masks = {}
        self.markings = {}
        self.signals = []
        self.scene_revision = 0
        self.direction_regions = []
        self.approach_resolver = ApproachResolver([])
        self.coverage = Counter()
        self.event_counts = Counter()
        self.frames = 0

    def analyze(self, result, original, video=False, scene_change=False):
        self.cancel()
        rgb = result.color_rgb
        original_resized = cv2.resize(original, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_AREA)
        if self.scene is None or scene_change:
            self.scene_id += 1
            self.perception.reset_tracks()
            self.rules.reset(self.scene_id)
            self.rider_associator.reset()
            self.trajectories.reset()
            self.turn_contexts.reset()
            self.camera.reset()
            proposal = self.scene_model.propose(original_resized)
            self.scene_proposals = [asdict(d) for d in proposal.detections]
            self.scene = SceneEvidence(scene_id=self.scene_id, source_evidence={"proposals": self.scene_proposals})
            self.cancel()
            masks, scores = self.segmenter.segment(original_resized)
            road = mask_polygons(masks.get("road", original_resized[:, :, 0] * 0))
            self.scene.approach_polygon = road[0] if road else []
            self.scene.footpath_polygons = mask_polygons(masks.get("sidewalk", original_resized[:, :, 0] * 0))
            self.scene.confidence = scores.get("road", 0.)
            self.scene.source_evidence["segmentation_scores"] = scores
            self._record_scene(original_resized, proposal, masks)
            self.scene_dirty = False
        self.cancel()
        detections = self.perception.detect(rgb, track=video)
        if video:
            stable, displacement = self.camera.observe(original_resized, result.timestamp, [d.box for d in detections if d.label != "traffic_light"])
            if self.scene.stationary_camera and not stable:
                self.rules.reset(self.scene_id)
            if displacement is not None and displacement > 1.5:
                self.scene_dirty = True
            if stable and self.scene_dirty:
                masks, scores = self.segmenter.segment(original_resized)
                road = mask_polygons(masks.get("road", original_resized[:, :, 0] * 0))
                self.scene.approach_polygon = road[0] if road else []
                self.scene.footpath_polygons = mask_polygons(masks.get("sidewalk", original_resized[:, :, 0] * 0))
                self.scene.confidence = scores.get("road", 0.)
                proposal = self.scene_model.propose(original_resized)
                self.scene_proposals = [asdict(d) for d in proposal.detections]
                self.scene.source_evidence = {"proposals": self.scene_proposals, "segmentation_scores": scores}
                self._record_scene(original_resized, proposal, masks)
                self.scene_dirty = False
            self.scene.stationary_camera = stable
            self.scene.source_evidence["camera_displacement"] = displacement
        self.signals = [signal_observation(original_resized, d, result.timestamp) for d in detections if d.label == "traffic_light"]
        self.approach_resolver.update_signals(self.signals, result.timestamp, self.scene.stationary_camera)
        motorcycles = [d for d in detections if d.label == "motorcycle"]
        people = [d for d in detections if d.label == "person"]
        heads = [d for d in detections if d.model == "iam-tsr/yolov8n-helmet-detection"]
        riders = (self.rider_associator.observe(motorcycles, people, heads, result.timestamp, self.scene.stationary_camera)
                  if video else associate_riders(motorcycles, people, heads))
        motorcycle_indices = {id(d): index for index, d in enumerate(motorcycles)}
        vehicles = [d for d in detections if d.label in {"bicycle", "car", "motorcycle", "bus", "truck"}]
        decisions = []
        self.turn_observations = []
        for vehicle in vehicles:
            rider = riders.get(motorcycle_indices.get(id(vehicle)))
            turn = self.trajectories.observe(vehicle, result.timestamp, self.scene.stationary_camera,
                                            self.scene.source_evidence.get("road_plane_transform")) if video else None
            if turn is not None:
                self.turn_observations.append(turn.to_dict())
            applicable = [region for region in self.direction_regions if point_in_polygon(vehicle.ground_point, region["polygon"])]
            vehicle_scene = self.approach_resolver.scene_for(vehicle, self.scene, result.timestamp)
            if len(applicable) == 1 and point_in_polygon(vehicle.ground_point, self.scene.approach_polygon):
                vehicle_scene = replace(vehicle_scene, permitted_direction=tuple(applicable[0]["direction"]), direction_polygon=applicable[0]["polygon"],
                                        source_evidence={**vehicle_scene.source_evidence, "direction_marking": applicable[0]})
            turn_context = self.turn_contexts.observe(vehicle, result.timestamp, vehicle_scene) if video else None
            resolved_turn = None
            if (turn and turn_context and turn.rule_turn is not None
                    and turn.entry_heading_ended_at <= turn_context["entry_timestamp"] <= turn.exit_heading_started_at):
                resolved_turn = turn.rule_turn
            decisions.extend(self.rules.evaluate(vehicle, result.timestamp, vehicle_scene, rider, video=video,
                                                 observed_turn=resolved_turn, turn_context=turn_context))
        if not vehicles:
            decisions = [Decision(rule, Verdict.UNKNOWN, "No eligible road user detected", result.timestamp) for rule in Rule]
        new_events, confirmed = self.events.update(decisions, result.timestamp, self.scene_id, image=not video)
        for decision in decisions:
            self.coverage[f"{decision.rule.value}/{decision.verdict.value}"] += 1
        for event in new_events:
            self.event_counts[event.rule.value] += 1
        self.frames += 1
        analysis = FrameAnalysis(result.timestamp, detections, decisions, self.scene_id)
        return annotate(rgb, confirmed), analysis, new_events

    def _record_scene(self, rgb, proposal, masks):
        self.turn_contexts.reset()
        self.scene_revision += 1
        self.scene_masks = masks
        self.markings, white = grounded_markings(rgb, proposal.detections, masks.get("road", rgb[:, :, 0] * 0))
        self.scene_masks["white_road_regions"] = white
        self.direction_regions = road_arrows(rgb, proposal.detections, masks.get("road", rgb[:, :, 0] * 0))
        approaches = infer_approaches(self.direction_regions, self.markings["stop_lines"], masks.get("road", rgb[:, :, 0] * 0))
        self.approach_resolver = ApproachResolver(approaches)
        self.approach_resolver.assign_crossings(self.markings["crossings"])
        sign_proposals = [d for d in proposal.detections if "traffic sign" in d.label and d.confidence >= .3
                          and min(d.box[2] - d.box[0], d.box[3] - d.box[1]) >= 24]
        sign_proposals = sign_candidates(rgb, sign_proposals)
        self.sign_observations = []
        if sign_proposals:
            if self.sign_classifier is None:
                self.status("Loading traffic-sign classifier. First use downloads weights.")
                self.sign_classifier = SignClassifier()
            for detection in sign_proposals:
                self.cancel()
                self.sign_observations.append(self.sign_classifier.classify(rgb, detection))
        self.cancel()
        if self.turn_sign_detector is None:
            self.status("Loading explicit turn-sign detector. First use downloads weights.")
            self.turn_sign_detector = TurnSignDetector(device=self.perception.device)
        self.cancel()
        self.sign_observations.extend(self.turn_sign_detector.detect(rgb))
        self.approach_resolver.assign_signs(self.sign_observations)
        self.scene.source_evidence["markings"] = self.markings
        self.scene.crossing_polygon = []

    def scene_snapshot(self):
        return {"scene_id": self.scene_id, "revision": self.scene_revision, "proposals": self.scene_proposals,
                "markings": self.markings, "segmentation": self.scene.source_evidence.get("segmentation_scores", {}),
                "road_polygon": self.scene.approach_polygon, "footpath_polygons": self.scene.footpath_polygons, "direction_regions": self.direction_regions,
                "sign_observations": self.sign_observations,
                "approaches": self.approach_resolver.approaches,
                "note": "Scene feature observations; legal direction and signal-to-approach assignment require additional evidence"}

    def summary(self):
        return {"frames": self.frames, "events_by_rule": dict(self.event_counts), "assessment_counts": dict(self.coverage),
                "device": self.perception.device, "coordinate_space": "IVP processed image; use coordinates.json to map to display-oriented source",
                "models": {**self.perception.manifest, "scene": {"repository": self.scene_model.MODEL, "revision": self.scene_model.REVISION, "device": self.scene_model.device},
                           "segmentation": {"repository": self.segmenter.MODEL, "revision": self.segmenter.REVISION},
                           "signs": {"repository": SignClassifier.MODEL, "revision": SignClassifier.REVISION, "loaded": self.sign_classifier is not None},
                           "turn_signs": self.turn_sign_detector.manifest if self.turn_sign_detector else {"loaded": False}},
                "scene_proposals": self.scene_proposals,
                "markings": self.markings, "signal_observations": self.signals,
                "sign_observations": self.sign_observations,
                "limitations": ["Experimental model results require review.", "Automatic legal scene association is still under development; unresolved rules return cannot_assess.",
                                "Geometric rider association has not yet been validated on crowded traffic.", "Model scores are not calibrated probabilities of a violation."]}
