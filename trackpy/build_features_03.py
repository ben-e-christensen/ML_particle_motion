#!/usr/bin/env python3
"""
build_features.py
-----------------
Loads linked trajectories, computes per-particle features, and saves summary CSVs.

Expected input:
    /media/ben/Extreme SSD/particles_ML/<timestamp>/linked_trajectories.csv

Outputs:
    trajectory_features.csv (aggregated stats)
    trajectory_features.png  (optional visualization)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import trackpy as tp

# === Config ===
BASE_DIR = "/media/ben/Extreme SSD/particles_ML"
RUN_FOLDER = max(
    [os.path.join(BASE_DIR, d) for d in os.listdir(BASE_DIR)
     if os.path.isdir(os.path.join(BASE_DIR, d))],
    key=os.path.getmtime
)
LINKED_FILE = os.path.join(RUN_FOLDER, "linked_trajectories.csv")
OUT_FILE = os.path.join(RUN_FOLDER, "trajectory_features.csv")

MIN_TRACK_LEN = 5       # ignore shorter tracks
N_PLOT = 1000            # number of random tracks to plot
SHOW_PLOTS = True
# ====================


def main():
    print(f"[i] Loading linked trajectories from {LINKED_FILE}")
    df = pd.read_csv(LINKED_FILE)
    print(f"[i] Loaded {len(df)} rows")

    # --- Verify essential columns ---
    if not {"x", "y", "frame", "particle"}.issubset(df.columns):
        raise ValueError("Input CSV must contain columns: x, y, frame, particle")

    # --- Remove very short tracks ---
    track_lens = df.groupby("particle")["frame"].count()
    long_particles = track_lens[track_lens >= MIN_TRACK_LEN].index
    df = df[df["particle"].isin(long_particles)]
    print(f"[✓] Retained {len(df)} points from {len(long_particles)} tracks (len ≥ {MIN_TRACK_LEN})")

    # --- Compute per-particle feature summary ---
    features = []
    for pid, g in df.groupby("particle"):
        g = g.sort_values("frame")
        dx = np.gradient(g["x"])
        dy = np.gradient(g["y"])
        speeds = np.sqrt(dx**2 + dy**2)
        turns = np.arctan2(np.gradient(dy), np.gradient(dx))

        features.append({
            "particle": pid,
            "n_frames": len(g),
            "duration": g["frame"].max() - g["frame"].min(),
            "speed_mean": np.mean(speeds),
            "speed_std": np.std(speeds),
            "turn_mean": np.mean(turns),
            "turn_std": np.std(turns),
            "mass_mean": g["mass"].mean() if "mass" in g.columns else np.nan,
            "ecc_mean": g["ecc"].mean() if "ecc" in g.columns else np.nan,
        })

    feats = pd.DataFrame(features)
    feats.to_csv(OUT_FILE, index=False)
    print(f"[✓] Saved feature table → {OUT_FILE}")
    print(feats.describe())

    # Optional trajectory visualization
    if SHOW_PLOTS:
        print("[plot] Drawing random sample of trajectories...")
        plt.figure(figsize=(8, 8))

        unique_particles = df['particle'].unique()

        if N_PLOT is None:
            subset_ids = unique_particles
        else:
            subset_ids = np.random.choice(unique_particles, size=min(N_PLOT, len(unique_particles)), replace=False)

        for pid in subset_ids:
            g = df[df['particle'] == pid]
            plt.plot(g['x'], g['y'], linewidth=0.8, alpha=0.7)

        plt.gca().invert_yaxis()
        plt.title(f"Sample of {len(subset_ids)} particle trajectories")
        plt.xlabel("x (px)")
        plt.ylabel("y (px)")
        plt.tight_layout()
        plt.show()



if __name__ == "__main__":
    main()
