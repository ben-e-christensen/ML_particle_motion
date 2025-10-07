#!/usr/bin/env python3
"""
Batch hyperuniformity analyzer for JPG images.

- Selects a circular ROI (Region of Interest) once.
- Computes isotropic structure factor S(k) for all .jpgs in the folder.
- Averages S(k) across images.
- Fits low-k region (S(k) ~ k^alpha) to get hyperuniformity exponent.

Requires:
  pip install numpy matplotlib scipy scikit-image
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from skimage.io import imread
from scipy.fft import fft2, fftshift
from scipy.ndimage import uniform_filter1d
from scipy.stats import linregress
from matplotlib.widgets import EllipseSelector
import json

# ---------------- Config ----------------
ROI_FILE = "roi.json"
EXTS = (".jpg", ".jpeg", ".png")
LOW_K_FIT_FRAC = 0.1  # fit first 10% of k-values
# ----------------------------------------

def select_circular_roi(img):
    """Interactive ROI selection: click once for center, once for edge."""
    pts = []
    fig, ax = plt.subplots()
    ax.imshow(img, cmap='gray')
    ax.set_title("Click center, then edge of desired circular ROI")

    def onclick(event):
        if event.xdata is None or event.ydata is None:
            return
        pts.append((event.xdata, event.ydata))
        ax.plot(event.xdata, event.ydata, 'ro')
        plt.draw()
        if len(pts) == 2:
            plt.close(fig)

    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()

    if len(pts) < 2:
        raise RuntimeError("ROI selection canceled.")
    (cx, cy), (ex, ey) = pts
    r = np.hypot(ex - cx, ey - cy)
    roi = {"cx": cx, "cy": cy, "r": r}
    with open(ROI_FILE, "w") as f:
        json.dump(roi, f, indent=2)
    print(f"[ROI] Saved to {ROI_FILE}")
    return roi

def load_or_select_roi(img):
    if os.path.exists(ROI_FILE):
        with open(ROI_FILE) as f:
            return json.load(f)
    else:
        return select_circular_roi(img)

def apply_circular_mask(img, cx, cy, r):
    Y, X = np.ogrid[:img.shape[0], :img.shape[1]]
    mask = (X - cx)**2 + (Y - cy)**2 <= r**2
    return np.where(mask, img, 0)

def compute_structure_factor(img):
    F = fftshift(fft2(img - np.mean(img)))
    S = np.abs(F)**2
    ny, nx = S.shape
    y, x = np.indices(S.shape)
    cx, cy = nx//2, ny//2
    r = np.sqrt((x - cx)**2 + (y - cy)**2).astype(int)
    tbin = np.bincount(r.ravel(), S.ravel())
    nr = np.bincount(r.ravel())
    radial_S = tbin / np.maximum(nr, 1)
    k = np.arange(len(radial_S))
    return k, radial_S / np.max(radial_S)

def fit_low_k_powerlaw(k, S):
    nfit = int(len(k) * LOW_K_FIT_FRAC)
    x = np.log10(k[1:nfit])
    y = np.log10(S[1:nfit])
    slope, intercept, r, p, stderr = linregress(x, y)
    alpha = slope
    return alpha, intercept, r**2

def main(folder):
    imgs = [os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(EXTS)]
    if not imgs:
        print("No images found.")
        return

    print(f"[INFO] Found {len(imgs)} images.")
    first = imread(imgs[0], as_gray=True)
    roi = load_or_select_roi(first)

    all_S = []
    for i, path in enumerate(imgs):
        img = imread(path, as_gray=True).astype(float)
        masked = apply_circular_mask(img, **roi)
        k, S = compute_structure_factor(masked)
        all_S.append(S)
        print(f"[{i+1}/{len(imgs)}] Processed {os.path.basename(path)}")

    S_mean = np.mean(all_S, axis=0)
    S_smooth = uniform_filter1d(S_mean, size=5)
    alpha, intercept, r2 = fit_low_k_powerlaw(k, S_smooth)

    plt.figure()
    plt.loglog(k[1:], S_smooth[1:], label=f"mean S(k)")
    fit_line = 10**intercept * k**alpha
    plt.loglog(k[1:], fit_line[1:], '--', label=f"fit α={alpha:.2f}, R²={r2:.3f}")
    plt.xlabel("k (pixels⁻¹)")
    plt.ylabel("S(k) (normalized)")
    plt.title("Average Structure Factor (ROI)")
    plt.legend()
    plt.grid(True, which='both', ls='--')
    plt.show()

if __name__ == "__main__":
    folder = input("Enter folder path containing JPGs: ").strip()
    main(folder)
