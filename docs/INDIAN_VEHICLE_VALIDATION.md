# Indian vehicle checkpoint evaluation - 24 September 2026

## Candidate and reproducibility

Source: https://huggingface.co/iisc-aim/UVH-26 . The IISc AIM repository provides models trained on Indian urban traffic and documents its class definitions. Upstream benchmark scores are not measurements of this project.

Tested weights/YOLOv11-S/UVH-26-MV-YOLOv11-S.pt at revision 4a22412775adb6f97f22735647afee976b4638a0. Size: 57,142,241 bytes. Verified SHA256: 12dbeb8f6fa207d19446fa652fc4313359fbec267027c8c01641004dcf1d0150. The checkpoint's actual 14 labels match the repository categories. Inference used the existing Ultralytics runtime, CUDA, 960-pixel input and confidence threshold 0.25, with the same BGR image input convention for both models.

Reproduce using temp/evaluate_uvh.py. Metadata: temp/qa/uvh_metadata.json. Raw candidate and baseline detections: temp/qa/uvh_comparison.json. Side-by-side inputs were identical; previews are temp/qa/uvh_0_uvh26.png through uvh_2_uvh26.png and corresponding coco previews. Weights stay under H:/CodexStorage/ivp-ai/models/uvh26-yolo11s-4a224127.pt.

## Visual findings on three development images

- demo/indian_riders.png: the central motorcycle is labelled Three-wheeler at 0.845, with another overlapping Three-wheeler prediction at 0.788. A foreground scooter is also labelled Three-wheeler at lower confidence.
- uploads/11431aa6634708477e92/image.png: one rear auto-rickshaw is correctly labelled Three-wheeler (0.889), but the large central auto-rickshaw attracts multiple Truck boxes (including 0.753 and 0.715), and the left foreground auto-rickshaw is also labelled Truck. Some motorcycles are detected as Two-wheeler. The baseline also mislabels auto-rickshaws as trucks; this candidate does not reliably resolve that failure.
- uploads/3140c803bd9be9e1f88f/image.png: the left foreground motorcycle/rider receives LCV, while the right foreground motorcycle is missed at the selected threshold. A distant Two-wheeler is detected at 0.722.

These are visually reviewed failure cases, not an independently labelled precision/recall benchmark. Their cause has not been established. Do not silently shift class indices, change labels or lower thresholds to force agreement with the examples.

## Integration decision

Do not replace or supplement the production road-user model with this checkpoint on the available evidence. Indian training provenance alone is insufficient to establish better detection on our camera views.

The repository defines two-wheeler and bicycle boxes as including the rider. Our existing association expects a motorcycle box separate from a person box, and applies head-above-motorcycle and relative-body geometry checks. Even a more accurate checkpoint using these annotations would require an explicit box-semantics adapter or different association method. It also lacks the person and traffic-light classes needed elsewhere in the pipeline; those cannot be dropped during a replacement.

Next work should compare compatible checkpoints or fine-tune on representative images with explicitly defined vehicle-only/person annotations. Retain these three cases as development regressions and use separate images for acceptance measurements. No model training or accuracy improvement is claimed from this evaluation.
