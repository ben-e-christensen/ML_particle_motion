import time, os
from gui.motor_controls import root as motor_root, run_gui
from gui.camera_feed import attach_camera_feed

def main():
    print("[RUN] Starting minimal dual-GUI app…")

    # Launch camera feed window attached to the same Tk root
    attach_camera_feed(parent=motor_root)

    # Run the main motor control GUI loop
    run_gui()

if __name__ == "__main__":
    main()
