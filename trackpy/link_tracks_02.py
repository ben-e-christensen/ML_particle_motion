#!/usr/bin/env python3
"""
Link particle detections into trajectories using TrackPy.
Input:  located_particles.csv  (from trackpy_batch_detect.py)
Output: linked_trajectories.csv with 'particle' IDs
"""

import os
import pandas as pd
import trackpy as tp

# --- Config ---
INPUT_CSV  = "/media/ben/Extreme SSD/particles_ML/2025-10-06_19-06-08/located_particles.csv"
OUTPUT_CSV = os.path.join(os.path.dirname(INPUT_CSV), "linked_trajectories.csv")
SEARCH_RANGE = 10   # max displacement (px) between frames
MEMORY = 3          # how many frames a particle can vanish and still be linked
# ----------------

def link_particles():
    if not os.path.exists(INPUT_CSV):
        print(f"[!] File not found: {INPUT_CSV}")
        return

    print(f"[i] Loading detections from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    if "frame_index" not in df.columns:
        print("[!] Missing 'frame_index' column. Did you run the batch detection first?")
        return

    print(f"[i] Linking trajectories (search_range={SEARCH_RANGE}, memory={MEMORY})…")
    df.rename(columns={"frame_index": "frame"}, inplace=True)

    linked = tp.link_df(df, search_range=SEARCH_RANGE, memory=MEMORY)

    print(f"[✓] Linked {linked['particle'].nunique()} unique particles.")
    linked.to_csv(OUTPUT_CSV, index=False)
    print(f"[✓] Saved linked trajectories to {OUTPUT_CSV}")

    # Quick summary
    track_lens = linked.groupby('particle')['frame_index'].count()
    print(f"[i] Track length summary:")
    print(track_lens.describe())

if __name__ == "__main__":
    link_particles()
