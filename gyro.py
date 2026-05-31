import time
import math
import board
import busio
import json
import os
import usb_hid
from adafruit_hid.mouse import Mouse
from sensor import MPU6500, QMC5883L
from mahony import Mahony

SAMPLE_RATE_HZ = 100
UPDATE_INTERVAL_NS = int(1e9 / SAMPLE_RATE_HZ)  # Convert to nanoseconds
CALIBRATION_FILE = "/calibration.json"

# Increase frequency to 400kHz for faster sensor polling
i2c = busio.I2C(scl=board.GP15, sda=board.GP14, frequency=400000)

m = Mouse(usb_hid.devices)

mpu = MPU6500(i2c)
mag = QMC5883L(i2c)

# Initialize Mahony Filter (Default Kp=0.5, Ki=0.0 are usually good starting points)
ahrs = Mahony(sample_freq=SAMPLE_RATE_HZ, Kp=10, Ki=0.0)

# State variable for non-blocking timer
last_update_time = time.monotonic_ns()

def calibrate_gyro(mpu):
    # Try to load existing calibration
    try:
        os.stat(CALIBRATION_FILE) # Check if file exists
        with open(CALIBRATION_FILE, "r") as f:
            offsets = json.load(f)
            print("Loaded saved gyro calibration!")
            return offsets["x"], offsets["y"], offsets["z"]
    except OSError:
        pass # File doesn't exist, proceed to calibrate

    # Run the calibration routine (from previous steps)
    print("No calibration found. Keep sensor perfectly still! Calibrating gyro...")
    x_off, y_off, z_off = 0.0, 0.0, 0.0
    samples = 200
    for _ in range(samples):
        gx, gy, gz = mpu.get_gyro()
        x_off += gx
        y_off += gy
        z_off += gz
        time.sleep(0.01)
        
    x_off /= samples
    y_off /= samples
    z_off /= samples
    
    # Try to save it for next time
    try:
        with open(CALIBRATION_FILE, "w") as f:
            json.dump({"x": x_off, "y": y_off, "z": z_off}, f)
        print("Calibration saved to flash!")
    except OSError:
        print("WARNING: Could not save to flash. Is boot.py set to readonly=False?")

    return x_off, y_off, z_off

# Run calibration before starting AHRS
gyro_off_x, gyro_off_y, gyro_off_z = calibrate_gyro(mpu)

def get_orientation():
    # 1. Read Raw Sensor Data
    ax, ay, az = mpu.get_acceleration()
    gx, gy, gz = mpu.get_gyro()
    raw_mx, raw_my, raw_mz = mag.get_mag()
    
    # Apply Calibration Offsets
    gx -= gyro_off_x
    gy -= gyro_off_y
    gz -= gyro_off_z
    
    # 2. Map Magnetometer Axes
    mx, my, mz = raw_my, raw_mx, -raw_mz
    
    # 3. Update the Mahony Filter
    # Note: Your MPU6500 class already scales gyro to degrees/sec, which Mahony requires.
    ahrs.update(gx, gy, gz, ax, ay, az, mx, my, mz)

    # 5. Retrieve and Convert Angles
    # invoke compute_angles() on demand and return radians.
    pitch_deg = math.degrees(ahrs.pitch)
    roll_deg = math.degrees(ahrs.roll)
    yaw_deg = math.degrees(ahrs.yaw)
    
    # Convert Pitch, Roll and Yaw to a continuous 0 to 180 degrees
    if abs(roll_deg) > 90:
        pitch_deg = -pitch_deg
    else:
        if pitch_deg >= 0:
            pitch_deg = pitch_deg - 180
        else:
            pitch_deg = pitch_deg + 180
    
    return pitch_deg, roll_deg, yaw_deg

    # (q0 is the scalar part, q1/q2/q3 are the vector parts)
    return ahrs.q0, ahrs.q1, ahrs.q2, ahrs.q3

print("Finding Center")
while True:
    pitchoff, rolloff, yawoff = get_orientation()
    if time.monotonic_ns() % 2_000_000_000 < 5_000_000: #2s
        break
print("Done")

print("Starting AHRS... Keep sensor still to allow filter to converge.")

PRINT_INTERVAL_NS = 50_000_000 #50ms
sen = 150
while True:
    pitch, roll, yaw = get_orientation()
    #q0, q1, q2, q3 = get_orientation()
    
    x = int((yaw - yawoff + 180) % 360 - 180)
    y = int((pitch - pitchoff + 180) % 360 - 180)
    
    x_value = int((-x / 180) * sen)
    y_value = int((y / 180) * sen)
    
    m.move(x_value, y_value)
    
    if time.monotonic_ns() % PRINT_INTERVAL_NS < 5_000_000:
        print(f"Pitch: {pitch}, Roll: {roll}, Yaw: {yaw}")
        print((x, y))
