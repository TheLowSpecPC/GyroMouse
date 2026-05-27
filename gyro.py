import time
import math
import struct
import board
import busio
import json
from mahony import Mahony
import sensor

CALIBRATION_FILE = "imu_cal.json"

# 1. Initialize Hardware
i2c = busio.I2C(scl=board.GP15, sda=board.GP14, frequency=400000)

# 2. Initialize Sensors
imu = sensor.MPU6500(i2c)
mag = sensor.QMC5883L(i2c)

# 3. Initialize Mahony Filter
ahrs = Mahony(Kp=0.5, Ki=0.0)

# ---------------------------------------------------------
# CALIBRATION SAVE/LOAD LOGIC
# ---------------------------------------------------------
def run_calibration():
    print("\n--- STARTING CALIBRATION ---")
    
    # --- GYRO CALIBRATION ---
    print("STEP 1: GYROSCOPE. Leave the sensor perfectly still for 5 seconds.")
    time.sleep(2) # Give user time to let go
    print("Calibrating Gyro...")
    
    gx_off, gy_off, gz_off = 0.0, 0.0, 0.0
    gyro_samples = 500
    for _ in range(gyro_samples):
        gx, gy, gz = imu.get_gyro()
        gx_off += gx
        gy_off += gy
        gz_off += gz
        time.sleep(0.002)
        
    gx_off /= gyro_samples
    gy_off /= gyro_samples
    gz_off /= gyro_samples
    
    # --- MAG CALIBRATION ---
    print("\nSTEP 2: MAGNETOMETER. Spin and tumble the sensor in a figure-8 pattern in ALL directions.")
    print("Starting in 3 seconds...")
    time.sleep(3)
    print("CALIBRATING MAG NOW! Keep moving it!")
    
    mag_min_x, mag_min_y, mag_min_z = 32767.0, 32767.0, 32767.0
    mag_max_x, mag_max_y, mag_max_z = -32768.0, -32768.0, -32768.0
    
    start_time = time.monotonic()
    while (time.monotonic() - start_time) < 15.0: # 15 seconds of tumbling
        mx, my, mz = mag.get_mag()
        
        mag_min_x, mag_max_x = min(mag_min_x, mx), max(mag_max_x, mx)
        mag_min_y, mag_max_y = min(mag_min_y, my), max(mag_max_y, my)
        mag_min_z, mag_max_z = min(mag_min_z, mz), max(mag_max_z, mz)
        time.sleep(0.005)
        
    # Calculate Hard-Iron Offsets
    mx_off = (mag_max_x + mag_min_x) / 2.0
    my_off = (mag_max_y + mag_min_y) / 2.0
    mz_off = (mag_max_z + mag_min_z) / 2.0
    
    # Calculate Soft-Iron Scales
    delta_x = (mag_max_x - mag_min_x) / 2.0
    delta_y = (mag_max_y - mag_min_y) / 2.0
    delta_z = (mag_max_z - mag_min_z) / 2.0
    avg_delta = (delta_x + delta_y + delta_z) / 3.0
    
    mx_scale = avg_delta / delta_x if delta_x != 0 else 1.0
    my_scale = avg_delta / delta_y if delta_y != 0 else 1.0
    mz_scale = avg_delta / delta_z if delta_z != 0 else 1.0

    cal_data = {
        "gyro_off": [gx_off, gy_off, gz_off],
        "mag_off": [mx_off, my_off, mz_off],
        "mag_scale": [mx_scale, my_scale, mz_scale]
    }
    
    try:
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(cal_data, f)
        print("Calibration saved successfully!")
    except OSError:
        print("Failed to save! Is boot.py set to readonly=False?")
        
    return cal_data

def get_calibration():
    try:
        with open(CALIBRATION_FILE, "r") as f:
            data = json.load(f)
            print("Loaded Calibration from file.")
            return data
    except (OSError, ValueError):
        return run_calibration()

# Load Data
cal = get_calibration()
g_off = cal["gyro_off"]
m_off = cal["mag_off"]
m_scale = cal["mag_scale"]

# ---------------------------------------------------------
# MAIN AHRS LOOP
# ---------------------------------------------------------
last_mag_time_ns = time.monotonic_ns()
mag_interval_ns = 5_000_000 # 200Hz
mx, my, mz = 0.0, 0.0, 0.0 

last_update_ns = time.monotonic_ns()
print("\nStarting AHRS. Tracking should now be stable.")

while True:
    current_ns = time.monotonic_ns()
    dt = (current_ns - last_update_ns) / 1_000_000_000.0
    
    if dt <= 0:
        continue 
        
    last_update_ns = current_ns
    ahrs.sample_freq = 1.0 / dt 

    # Read and Offset IMU
    gx, gy, gz = imu.get_gyro()
    ax, ay, az = imu.get_acceleration()
    
    gx -= g_off[0]
    gy -= g_off[1]
    gz -= g_off[2]

    # Read and Calibrate Magnetometer
    if (current_ns - last_mag_time_ns) >= mag_interval_ns:
        raw_mx, raw_my, raw_mz = mag.get_mag()
        
        # Apply Hard-Iron Offset and Soft-Iron Scale
        mx = (raw_mx - m_off[0]) * m_scale[0]
        my = (raw_my - m_off[1]) * m_scale[1]
        mz = (raw_mz - m_off[2]) * m_scale[2]
        
        last_mag_time_ns = current_ns

    # ---------------------------------------------------------
    # AXIS MAPPING (CRITICAL)
    # ---------------------------------------------------------
    # The QMC5883L silicon is usually rotated relative to the MPU6500.
    # If Pitch/Roll movements cause your Yaw to aggressively twist, 
    # you need to rearrange these variables to match the physical arrows 
    # printed on your sensor breakout board.
    
    mx_mapped = my
    my_mapped = mx
    mz_mapped = -mz
    
    # ---------------------------------------------------------
    # Update Filter
    # ---------------------------------------------------------
    ahrs.update(gx, gy, gz, ax, ay, az, mx_mapped, my_mapped, mz_mapped) 

    # Convert to Degrees
    roll_deg  = ahrs.roll * (180.0 / math.pi)
    pitch_deg = ahrs.pitch * (180.0 / math.pi)
    yaw_deg   = ahrs.yaw * (180.0 / math.pi)

    print(f"Pitch: {pitch_deg:.2f} | Roll: {roll_deg:.2f} | Yaw: {yaw_deg:.2f}")