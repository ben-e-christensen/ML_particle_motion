#!/usr/bin/env python3
"""
Single-image TrackPy ROI selector + particle detector.
- First run: asks user to click center & edge to define ROI.
- Saves ROI to 'roi.json' for reuse.
- Later runs: automatically loads ROI and applies same circular mask.
"""

import numpy as np
import pandas as pd
import pims
import trackpy as tp
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import os, sys, json

# --- Config ---
IMAGE_FILENAME = "frame.jpg"
ROI_FILE = "roi.json"
ESTIMATED_DIAMETER = 9
MIN_MASS_CUTOFF = 500
# ---------------------

def load_or_create_roi(frame):
    """Load ROI from file, or ask user to define one."""
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE, "r") as f:
                data = json.load(f)
                if all(k in data for k in ["cx", "cy", "r"]):
                    print(f"[ROI] Loaded existing ROI from {ROI_FILE}")
                    return data["cx"], data["cy"], data["r"]
        except Exception:
            pass

    # --- Ask user to define new ROI ---
    print("\n--- Define Circular ROI (2 Clicks) ---")
    print("Click 1: Center (crosshatch shows)")
    print("Click 2: Edge (defines radius)")

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(frame, cmap='gray')
    ax.set_title("Click 1: Center, then Click 2: Edge (to define radius)")

    clicks = plt.ginput(n=2, timeout=60, show_clicks=True)
    plt.close(fig)

    if len(clicks) < 2:
        print("[ROI] No valid clicks — using full image.")
        return None

    (x_c, y_c), (x_e, y_e) = clicks
    r = np.sqrt((x_e - x_c)**2 + (y_e - y_c)**2)
    roi = {"cx": int(x_c), "cy": int(y_c), "r": float(r)}

    with open(ROI_FILE, "w") as f:
        json.dump(roi, f, indent=2)
    print(f"[ROI] Saved to {ROI_FILE}")

    return roi["cx"], roi["cy"], roi["r"]


def apply_circular_mask(frame, cx, cy, r):
    """Zeroes out pixels outside a circular ROI."""
    Y, X = np.ogrid[:frame.shape[0], :frame.shape[1]]
    mask = (X - cx)**2 + (Y - cy)**2 > r**2
    masked = frame.copy()
    masked[mask] = 0
    return masked


def run_trackpy_location():
    if not os.path.exists(IMAGE_FILENAME):
        print(f"[!] Image not found: {IMAGE_FILENAME}")
        return

    frame = pims.open(IMAGE_FILENAME)[0]
    if frame.ndim == 3:
        frame = np.mean(frame, axis=2).astype(frame.dtype)

    roi_data = load_or_create_roi(frame)
    if roi_data is None:
        process_frame = frame
        cx = cy = r = None
    else:
        cx, cy, r = roi_data
        process_frame = apply_circular_mask(frame, cx, cy, r)

    print(f"[tp] Running locate() with diameter={ESTIMATED_DIAMETER}, minmass={MIN_MASS_CUTOFF}")
    f = tp.locate(process_frame, ESTIMATED_DIAMETER, minmass=MIN_MASS_CUTOFF)

    print(f"[tp] Found {len(f)} particles.")
    if len(f) > 0:
        print(f[['x', 'y', 'mass', 'size', 'ecc']].head())

    # --- Plot results ---
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(process_frame, cmap='gray')

    if roi_data:
        circle = Circle((cx, cy), r, edgecolor='yellow', facecolor='none', linewidth=2)
        ax.add_patch(circle)

    if len(f) > 0:
        ax.scatter(f['x'], f['y'], s=10, c='r', marker='o')

    ax.set_title(f"Detected particles ({len(f)} found)")
    plt.savefig("located_particles_clean_output.png", bbox_inches='tight', dpi=300)
    print("[i] Saved output image to located_particles_clean_output.png")
    plt.show()


if __name__ == "__main__":
    run_trackpy_location()
