"""Reproducible image-space marking survey; no learned models or semantic labels."""
import math

import cv2
import numpy as np


def survey(rgb, rectangle, transform=None):
    if (not isinstance(rectangle, list) or len(rectangle) != 4 or
        any(isinstance(v, bool) or not isinstance(v, (int, float)) or
            not math.isfinite(v) or not 0 <= v <= 1 for v in rectangle)):
        raise ValueError('Select a road region using four normalized coordinates.')
    x1, y1, x2, y2 = rectangle
    h, w = rgb.shape[:2]
    left, top, right, bottom = int(x1*w), int(y1*h), math.ceil(x2*w), math.ceil(y2*h)
    if right-left < 16 or bottom-top < 16:
        raise ValueError('Select a road region at least 16 pixels wide and high.')
    crop = rgb[top:bottom, left:right].copy()
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hue, sat, value = cv2.split(hsv)
    # Otsu separates bright paint-like pixels from the selected road's value
    # distribution. A dark floor and a flat-region check prevent trivial masks.
    otsu, _ = cv2.threshold(value, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    floor = max(100, min(230, int(otsu) + 1))
    flat = float(np.percentile(value, 99)-np.percentile(value, 1)) < 20
    kernel = np.ones((3, 3), np.uint8)
    min_area = max(20, math.ceil(gray.size * .0005))

    def segment(threshold):
        white = (sat <= 65) & (value >= threshold)
        yellow = (hue >= 15) & (hue <= 38) & (sat >= 70) & (value >= threshold)
        raw = ((white | yellow) * 255).astype(np.uint8)
        if flat:
            raw[:] = 0
        cleaned = cv2.morphologyEx(raw, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned)
        keep = np.zeros(count, np.uint8)
        keep[1:] = (stats[1:, cv2.CC_STAT_AREA] >= min_area) * 255
        return raw, keep[labels]

    raw, mask = segment(floor)
    _, low = segment(max(0, floor-20))
    _, high = segment(min(255, floor+20))
    union = (low > 0) | (high > 0)
    agreement = float(np.count_nonzero((low > 0) & (high > 0))/union.sum()) if union.any() else None
    count, labels, stats, centres = cv2.connectedComponentsWithStats(mask)
    overlay = crop.copy()
    overlay[mask > 0] = (crop[mask > 0]*.35 + np.array([20, 180, 210])*.65).astype(np.uint8)
    transform = np.eye(3) if transform is None else np.asarray(transform)
    rows = []
    for i in range(1, count):
        x, y, width, height, area = map(int, stats[i])
        yy, xx = np.nonzero(labels[y:y+height, x:x+width] == i)
        points = np.column_stack((xx+x, yy+y)).astype(np.float32)
        _, (side_a, side_b), _ = cv2.minAreaRect(points)
        covariance = np.cov(points, rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        direction = vectors[:, -1]
        angle = float(np.degrees(np.arctan2(direction[1], direction[0])) % 180)
        orientation = angle if values[-1] > 1.2*max(values[0], 1e-9) else None
        cx, cy = map(float, centres[i])
        source = transform @ [cx+left, cy+top, 1]
        row = {'id': i, 'area_px': area, 'bbox_x': x+left, 'bbox_y': y+top,
               'bbox_width_px': width, 'bbox_height_px': height,
               'long_side_px': float(max(side_a, side_b)), 'short_side_px': float(min(side_a, side_b)),
               'orientation_deg_clockwise_from_right': orientation,
               'touches_roi_boundary': bool(x == 0 or y == 0 or x+width == crop.shape[1] or y+height == crop.shape[0]),
               'source_centre_x': float(source[0]/source[2]), 'source_centre_y': float(source[1]/source[2])}
        rows.append(row)
        cv2.rectangle(overlay, (x, y), (x+width-1, y+height-1), (255, 180, 20), 1)
        cv2.putText(overlay, str(i), (x, max(12, y+12)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 70, 20), 1)
    warnings = ['White vehicles, reflections and other bright surfaces can enter the mask. Select road only and review the overlay.',
                'Coverage describes visible candidate pixels, not paint wear, road occupancy or physical area. Perspective and occlusion affect results.']
    if not rows:
        warnings.append('No retained bright white/yellow fragments. This does not prove markings are absent; dark or faded markings can be missed.')
    if flat:
        warnings.append('Too little brightness separation in this selection; segmentation is withheld. Include both road and markings.')
    if agreement is not None and agreement < .75:
        warnings.append('Segmentation changes substantially under a ±20 brightness-threshold test. Inspect both sensitivity masks.')
    if any(r['touches_roi_boundary'] for r in rows):
        warnings.append('Some fragments touch the selection boundary and may be truncated.')
    report = {'method': 'classical_marking_survey_v1', 'uses_ai': False,
              'roi_normalized': rectangle, 'roi_xyxy_exclusive': [left, top, right, bottom],
              'analysis_size': [w, h], 'transform_to_source_pixel_centres': transform.tolist(),
              'parameters': {'brightness_threshold': floor, 'otsu_value': float(otsu),
                             'threshold_rule': 'Otsu value + 1, bounded to 100–230; withhold if p99-p1 < 20',
                             'white_saturation_max': 65,
                             'yellow_hue_range': [15, 38], 'yellow_saturation_min': 70,
                             'morphology': 'open then close, 3x3', 'minimum_component_area_px': min_area},
              'summary': {'roi_area_px': int(gray.size), 'candidate_area_px': int(np.count_nonzero(mask)),
                          'coverage_percent': float(np.mean(mask > 0)*100), 'fragments': len(rows),
                          'threshold_low_coverage_percent': float(np.mean(low > 0)*100),
                          'threshold_high_coverage_percent': float(np.mean(high > 0)*100),
                          'threshold_mask_iou': agreement},
              'fragments': rows, 'limitations': warnings}
    return report, {'selected-road': crop, 'raw-segmentation': raw, 'cleaned-mask': mask,
                    'threshold-minus-20': low, 'threshold-plus-20': high, 'annotated-survey': overlay}
