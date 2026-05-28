import time
import math
import board
import busio
import json
import os
from sensor import MPU6500, QMC5883L
from mahony import Mahony

SAMPLE_RATE_HZ = 100
UPDATE_INTERVAL_NS = int(1e9 / SAMPLE_RATE_HZ)  # Convert to nanoseconds
CALIBRATION_FILE = "/calibration.json"

# Increase frequency to 400kHz for faster sensor polling
i2c = busio.I2C(scl=board.GP15, sda=board.GP14, frequency=400000)

mpu = MPU6500(i2c)
mag = QMC5883L(i2c)

# Initialize Mahony Filter (Default Kp=0.5, Ki=0.0 are usually good starting points)
ahrs = Mahony(sample_freq=SAMPLE_RATE_HZ, Kp=0.5, Ki=0.0)

# State variable for non-blocking timer
last_update_time = time.monotonic_ns()

def calibrate_gyro(mpu):
    # Try to load existing calibration
    try:
        os.stat(CALIBRATION_FILE) # Check if file exists
        with open(CALIBRATION_FILE, "r") as f:
            offsets = json.load(f)
            return offsets["x"], offsets["y"], offsets["z"]
    except OSError:
        pass # File doesn't exist, proceed to calibrate

    # Run the calibration routine (from previous steps)
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
    except OSError:
        pass

    return x_off, y_off, z_off

def get_orientation():
    global last_update_time
    
    current_time = time.monotonic_ns()
    
    # Non-blocking check: execute only if the interval has elapsed
    if (current_time - last_update_time) >= UPDATE_INTERVAL_NS:
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
        
        # 4. Reset Timer (Add interval instead of setting to current_time to avoid drift)
        last_update_time += UPDATE_INTERVAL_NS

    # 5. Retrieve and Convert Angles
    # invoke compute_angles() on demand and return radians.
    pitch_deg = math.degrees(ahrs.pitch)
    roll_deg = math.degrees(ahrs.roll)
    yaw_deg = math.degrees(ahrs.yaw)
    
    #return pitch_deg, roll_deg, yaw_deg

    # (q0 is the scalar part, q1/q2/q3 are the vector parts)
    return ahrs.q0, ahrs.q1, ahrs.q2, ahrs.q3

# Run calibration before starting AHRS
gyro_off_x, gyro_off_y, gyro_off_z = calibrate_gyro(mpu)

PRINT_INTERVAL_NS = 20_000_000 #20ms
while True:
    q0, q1, q2, q3 = get_orientation()
    
    if time.monotonic_ns() % PRINT_INTERVAL_NS < 5_000_000:
        print(f"{q0},{q1},{q2},{q3}")

