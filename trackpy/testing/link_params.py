#!/usr/bin/env python3
"""
link_param_sweep.py
Sweeps through combinations of (search_range, memory) to evaluate
trajectory continuity quality using Trackpy.

It prints:
- number of unique tracks
- mean & median track lengths
- % of tracks longer than 10 frames
so you can judge which parameters keep continuity best.

Usage:
    python3 link_param_sweep.py /path/to/located_particles.csv
"""

import sys, os
import pandas as pd
import numpy as np
import trackpy as tp
from itertools import product

# --- CONFIG ---
SEARCH_RANGES = [5, 10, 15, 20, 25]   # px
MEMORIES = [1, 3, 5, 8, 10]
THRESHOLD_LONG = 10                   # minimum frames to count as "long"

def analyze_params(df, search_range, memory):
    linked = tp.link_df(df, search_range=search_range, memory=memory, adaptive_stop=True)
    grouped = linked.groupby('particle')['frame'].count()
    n_tracks = len(grouped)
    mean_len = grouped.mean()
    median_len = grouped.median()
    pct_long = (grouped >= THRESHOLD_LONG).mean() * 100
    return n_tracks, mean_len, median_len, pct_long

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 link_param_sweep.py located_particles.csv")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        sys.exit(1)

    print(f"[i] Loading detections from: {path}")
    df = pd.read_csv(path)
    if 'frame' not in df.columns:
        print("[!] CSV must contain 'frame' column.")
        sys.exit(1)

    results = []
    print("[i] Running parameter sweep...\n")

    for search_range, memory in product(SEARCH_RANGES, MEMORIES):
        n_tracks, mean_len, median_len, pct_long = analyze_params(df, search_range, memory)
        results.append({
            'search_range': search_range,
            'memory': memory,
            'n_tracks': n_tracks,
            'mean_len': mean_len,
            'median_len': median_len,
            'pct_long': pct_long
        })
        print(f"Range={search_range:>2}px | Mem={memory:>2} | Tracks={n_tracks:>5} | "
              f"Mean={mean_len:6.1f} | Median={median_len:6.1f} | ≥{THRESHOLD_LONG}f={pct_long:5.1f}%")

    res_df = pd.DataFrame(results)
    out_csv = os.path.join(os.path.dirname(path), "link_sweep_results.csv")
    res_df.to_csv(out_csv, index=False)
    print(f"\n[✓] Saved results → {out_csv}")
    print(res_df)

if __name__ == "__main__":
    main()
