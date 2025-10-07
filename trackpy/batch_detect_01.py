#!/usr/bin/env python3
"""
Batch Trackpy particle detection with circular ROI
- Base directory: /media/ben/Extreme SSD/particles_ML/
- Usage: python3 track_particles_batch.py <timestamp_folder_name>
- Looks for images in: BASE_DIR/<timestamp>/images/
- Saves located_particles.csv in BASE_DIR/<timestamp>/
"""

import os, json, sys, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import trackpy as tp
from skimage.io import imread

# --- Config ---
BASE_DIR = "/media/ben/Extreme SSD/particles_ML"
ROI_FILE = "roi.json"
DIAMETER = 9
MINMASS = 500
INVERT = False
# ---------------

def load_or_define_roi(sample_img):
    """Load roi.json if exists, otherwise let user click center and edge."""
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE, "r") as f:
                roi = json.load(f)
            if all(k in roi for k in ("cx", "cy", "r")) and roi["r"] > 0:
                print(f"[roi] Loaded ROI from {ROI_FILE}: {roi}")
                return roi
            else:
                print("[roi] File found but incomplete, requesting new ROI…")
        except Exception as e:
            print(f"[roi] Failed to read roi.json: {e}")

    # Ask user for ROI via two clicks
    print("[roi] Define circular ROI (click center, then edge)…")
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(sample_img, cmap="gray")
    plt.title("Click center, then edge of ROI")
    pts = plt.ginput(2, timeout=60)
    plt.close(fig)
    if len(pts) != 2:
        raise RuntimeError("ROI selection failed (2 clicks required)")

    (cx, cy), (ex, ey) = pts
    r = ((ex - cx)**2 + (ey - cy)**2)**0.5
    roi = {"cx": int(cx), "cy": int(cy), "r": int(r)}
    with open(ROI_FILE, "w") as f:
        json.dump(roi, f, indent=2)
    print(f"[roi] Saved new ROI → {ROI_FILE}")
    return roi


def apply_circular_mask(img, roi):
    """Apply circular mask to image."""
    cx, cy, r = roi["cx"], roi["cy"], roi["r"]
    Y, X = np.ogrid[:img.shape[0], :img.shape[1]]
    mask = (X - cx)**2 + (Y - cy)**2 > r**2
    result = img.copy()
    result[mask] = 0
    return result


def process_image_sequence(timestamp):
    run_dir = os.path.join(BASE_DIR, timestamp)
    images_dir = os.path.join(run_dir, "images")

    if not os.path.exists(images_dir):
        print(f"[!] Could not find image directory: {images_dir}")
        sys.exit(1)

    images = sorted(glob.glob(os.path.join(images_dir, "*.jpg")))
    if not images:
        print(f"[!] No images found in {images_dir}")
        sys.exit(1)

    print(f"[i] Found {len(images)} images in {images_dir}")
    sample_img = imread(images[0])
    roi = load_or_define_roi(sample_img)

    out_csv = os.path.join(run_dir, "located_particles.csv")
    all_frames = []

    for i, path in enumerate(images):
        img = imread(path)
        if img.ndim == 3:
            img = np.mean(img, axis=2).astype(np.uint8)
        masked = apply_circular_mask(img, roi)
        f = tp.locate(masked, DIAMETER, minmass=MINMASS, invert=INVERT)
        f["frame"] = i
        f["filename"] = os.path.basename(path)
        all_frames.append(f)

        print(f"[{i+1}/{len(images)}] Found {len(f)} particles in {os.path.basename(path)}")

    df = pd.concat(all_frames, ignore_index=True)
    df.to_csv(out_csv, index=False)
    print(f"[✓] Saved all detections → {out_csv}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 track_particles_batch.py <timestamp_folder_name>")
        sys.exit(1)
    process_image_sequence(sys.argv[1])
