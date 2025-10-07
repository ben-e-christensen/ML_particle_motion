import tkinter as tk
import serial, time, sys

# ===== Config =====
SERIAL_PORT = "/dev/ttyACM0"
BAUD = 115200
STEPS_PER_REV = 6400  # adjust if microstepping

# ===== Serial Setup =====
try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
    time.sleep(2)
    print(f"[i] Serial connected on {SERIAL_PORT} @ {BAUD}")
except serial.SerialException as e:
    print(f"[!] Serial error: {e}")
    ser = None

# ===== Helper: send command =====
def send_command(cmd, val=None):
    """Send simple serial command like S###, X, T, etc."""
    if not ser:
        print("[!] Serial not connected.")
        return
    msg = f"{cmd}{val if val is not None else ''}\n".encode()
    try:
        ser.write(msg)
    except Exception as e:
        print(f"[!] Serial write failed: {e}")

# ===== GUI root =====
root = tk.Tk()
root.title("Motor Controls")

# ===== GUI State =====
motor_state = {
    "rpm": 1,
    "spr": STEPS_PER_REV,
    "running": False,
}

inc_val = tk.StringVar(value="1")  # RPM increment value

# ===== Helper functions =====
def calculate_sps(rpm):
    """Convert RPM → steps/sec based on steps per rev."""
    return (rpm / 60.0) * motor_state["spr"]

def update_display():
    """Update labels for steps/sec and deg/sec."""
    try:
        rpm = float(freq_entry.get())
    except ValueError:
        rpm = motor_state["rpm"]
    sps = calculate_sps(rpm)
    dps = (rpm / 60.0) * 360.0
    info_label.config(
        text=f"Steps/sec: {sps:.1f}\nDegrees/sec: {dps:.1f}"
    )

def adjust_speed(direction):
    """Increase or decrease RPM and send new speed."""
    try:
        current_rpm = float(freq_entry.get())
        inc = float(inc_val.get())
    except ValueError:
        print("[!] Invalid RPM or increment value.")
        return

    new_rpm = current_rpm + inc if direction == "up" else current_rpm - inc
    motor_state["rpm"] = max(new_rpm, 0)
    freq_entry.delete(0, tk.END)
    freq_entry.insert(0, str(motor_state["rpm"]))

    sps = int(calculate_sps(motor_state["rpm"]))
    send_command("S", sps)
    motor_state["running"] = True
    update_display()
    status_label.config(text=f"Running @ {motor_state['rpm']} RPM")

def start_motor():
    try:
        rpm = float(freq_entry.get())
    except ValueError:
        print("[!] Invalid RPM entry.")
        return
    sps = int(calculate_sps(rpm))
    send_command("S", sps)
    motor_state["running"] = True
    update_display()
    status_label.config(text=f"Running @ {rpm} RPM")
    print(f"[MOTOR] Start @ {rpm} RPM ({sps} SPS)")

def stop_motor():
    send_command("X")
    motor_state["running"] = False
    status_label.config(text="Stopped")
    print("[MOTOR] Stop")

def reverse_motor():
    send_command("T")
    print("[MOTOR] Reverse direction")

def find_origin():
    send_command("L")
    print("[MOTOR] Find origin (homing)")

def handle_enter(event=None):
    start_motor()

# ===== Graceful Exit =====
def on_close():
    """Stop motor, close serial, and exit safely."""
    print("[EXIT] Shutting down gracefully...")
    try:
        stop_motor()
    except Exception:
        pass
    try:
        if ser and ser.is_open:
            ser.close()
            print("[EXIT] Serial port closed.")
    except Exception as e:
        print(f"[EXIT] Serial close error: {e}")
    root.destroy()
    sys.exit(0)

root.protocol("WM_DELETE_WINDOW", on_close)

# ===== GUI Layout =====
frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="Target Speed (RPM):").pack()
freq_entry = tk.Entry(frame, width=10)
freq_entry.insert(0, "1")
freq_entry.pack(pady=3)

info_label = tk.Label(frame, text="", fg="gray")
info_label.pack(pady=3)

status_label = tk.Label(frame, text="Idle", fg="blue")
status_label.pack(pady=5)

# Speed controls
speed_frame = tk.Frame(frame)
speed_frame.pack(pady=5)
tk.Label(speed_frame, text="Increment (RPM):").grid(row=0, column=0, padx=3)
tk.Entry(speed_frame, width=6, textvariable=inc_val).grid(row=0, column=1, padx=3)
tk.Button(speed_frame, text="Speed ↑", command=lambda: adjust_speed("up")).grid(row=0, column=2, padx=3)
tk.Button(speed_frame, text="Speed ↓", command=lambda: adjust_speed("down")).grid(row=0, column=3, padx=3)

# Control buttons
btn_frame = tk.Frame(frame)
btn_frame.pack(pady=8)
tk.Button(btn_frame, text="Start", width=10, command=start_motor).grid(row=0, column=0, padx=4)
tk.Button(btn_frame, text="Stop", width=10, command=stop_motor).grid(row=0, column=1, padx=4)
tk.Button(btn_frame, text="Reverse", width=10, command=reverse_motor).grid(row=0, column=2, padx=4)
tk.Button(btn_frame, text="Find Origin", width=12, command=find_origin).grid(row=0, column=3, padx=4)

root.bind("<Return>", handle_enter)
root.bind("<KP_Enter>", handle_enter)

def run_gui():
    print("[GUI] Motor control ready.")
    update_display()
    root.mainloop()
