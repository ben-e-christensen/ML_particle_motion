import tkinter as tk
import threading, queue, time, os
from datetime import datetime
from PIL import Image, ImageTk
import cv2
from pypylon import pylon

# UI refresh target (30 FPS)
TARGET_UI_FPS = 30
# Desired image save rate (50 FPS)
SAVE_RATE = 60.0
TARGET_SAVE_INTERVAL = 1.0 / SAVE_RATE  # 10 ms

# === Base session path ===
BASE_DIR = "/media/ben/Extreme SSD/particles_ML"
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Session folder (e.g. /media/ben/Extreme SSD/particles_ML/2025-10-06_21-15-32)
RUN_DIR = os.path.join(BASE_DIR, timestamp)
IMAGES_DIR = os.path.join(RUN_DIR, "images")

# Create both folders
os.makedirs(IMAGES_DIR, exist_ok=True)

print(f"[save] Session folder: {RUN_DIR}")
print(f"[save] Images will be saved to: {IMAGES_DIR}")

class CameraGrabber(threading.Thread):
    def __init__(self, q, stop_event):
        super().__init__(daemon=True)
        self.q = q
        self.stop_event = stop_event
        self.cam = None
        self.converter = None
        self.err = None
        self.frame_index = 0
        self.last_save_time = 0

    def run(self):
        try:
            tl = pylon.TlFactory.GetInstance()
            devs = tl.EnumerateDevices()
            if not devs:
                self.err = "No Basler camera found"
                return

            self.cam = pylon.InstantCamera(tl.CreateFirstDevice())
            self.cam.Open()
            print("[camera] Connected:", self.cam.GetDeviceInfo().GetModelName())

            self.cam.GainAuto.SetValue("Off")
            self.cam.Gain.SetValue(25.0)
            self.cam.PixelFormat.SetValue("Mono8")

            self.converter = pylon.ImageFormatConverter()
            self.converter.OutputPixelFormat = pylon.PixelType_Mono8
            self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

            self.cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

            while not self.stop_event.is_set() and self.cam.IsGrabbing():
                grab = self.cam.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                if grab.GrabSucceeded():
                    frame = self.converter.Convert(grab).GetArray()

                    # Push to UI queue (for display)
                    try:
                        self.q.put_nowait(frame)
                    except queue.Full:
                        pass

                    # --- Save frame at 100 FPS ---
                    now = time.time()
                    if now - self.last_save_time >= TARGET_SAVE_INTERVAL:
                        filename = os.path.join(IMAGES_DIR, f"frame_{self.frame_index:06d}.jpg")
                        cv2.imwrite(filename, frame)
                        self.last_save_time = now
                        self.frame_index += 1

                grab.Release()

        except Exception as e:
            self.err = str(e)

        finally:
            try:
                if self.cam:
                    self.cam.StopGrabbing()
                    self.cam.Close()
            except Exception:
                pass
            print("[camera] Stopped grabbing.")

def _build_camera_window(parent):
    top = tk.Toplevel(parent)
    top.title("Basler Camera Feed (Saving @ 60 FPS)")
    label = tk.Label(top)
    label.pack(fill="both", expand=True)
    info = tk.Label(top, text="Starting camera…")
    info.pack(anchor="w")

    q = queue.Queue(maxsize=2)
    stop_event = threading.Event()
    grabber = CameraGrabber(q, stop_event)
    grabber.start()
    tk_image = None

    def update_ui():
        nonlocal tk_image
        frame = None
        try:
            while True:
                frame = q.get_nowait()
        except queue.Empty:
            pass

        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            img = Image.fromarray(rgb)
            tk_image = ImageTk.PhotoImage(img)
            label.config(image=tk_image)

        if grabber.err:
            info.config(text=f"[!] {grabber.err}")
        else:
            info.config(text=f"Streaming… {grabber.frame_index} frames saved")

        top.after(int(1000 / TARGET_UI_FPS), update_ui)

    def on_close():
        stop_event.set()
        top.destroy()

    top.protocol("WM_DELETE_WINDOW", on_close)
    top.after(100, update_ui)
    return top

def attach_camera_feed(parent=None):
    root = parent or tk._get_default_root()
    if root is None:
        root = tk.Tk()
        _build_camera_window(root)
        root.mainloop()
    else:
        _build_camera_window(root)

if __name__ == "__main__":
    attach_camera_feed()
