import time
import math
import board
import busio
import json
import os
import usb_hid
from ulab import numpy as np
from adafruit_hid.mouse import Mouse
from sensor import MPU6500, QMC5883L
from mahony import Mahony


class Gyro:
    def __init__(self, i2c_bus, mouse, CalFile = "/Calibration/GyroCalibration.json"):
        self.SAMPLE_RATE_HZ = 100
        self.UPDATE_INTERVAL_NS = int(1e9 / self.SAMPLE_RATE_HZ)  # Convert to nanoseconds
        self.CALIBRATION_FILE = CalFile

        # Increase frequency to 400kHz for faster sensor polling
        self.i2c = i2c_bus

        self.m = mouse

        self.mpu = MPU6500(self.i2c)
        self.mag = QMC5883L(self.i2c)

        # Initialize Mahony Filter
        self.ahrs = Mahony(sample_freq=self.SAMPLE_RATE_HZ, Kp=0.05, Ki=0.0)

        # State variable for non-blocking timer
        self.last_update_time = time.monotonic_ns()
        
        self.inrange = 180
        self.outrangey = 6000
        self.outrangex = self.outrangey+(1920/1080)
        self.xnot, self.ynot = 0, 0
        
        # Run calibration before starting AHRS
        self.gyro_off_x, self.gyro_off_y, self.gyro_off_z = 0,0,0
        self.calibrate_gyro(self.mpu)
        
        self.pitchoff, self.rolloff, self.yawoff = 0,0,0

    def calibrate_gyro(self, mpu):
        # Try to load existing calibration
        try:
            os.stat(self.CALIBRATION_FILE) # Check if file exists
            with open(self.CALIBRATION_FILE, "r") as f:
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
            gx, gy, gz = self.mpu.get_gyro()
            x_off += gx
            y_off += gy
            z_off += gz
            time.sleep(0.01)
            
        x_off /= samples
        y_off /= samples
        z_off /= samples
        
        # Try to save it for next time
        try:
            with open(self.CALIBRATION_FILE, "w") as f:
                json.dump({"x": x_off, "y": y_off, "z": z_off}, f)
            print("Calibration saved to flash!")
        except OSError:
            print("WARNING: Could not save to flash. Is boot.py set to readonly=False?")

        self.gyro_off_x, self.gyro_off_y, self.gyro_off_z = x_off, y_off, z_off

    def get_orientation(self):
        # 1. Read Raw Sensor Data
        ax, ay, az = self.mpu.get_acceleration()
        gx, gy, gz = self.mpu.get_gyro()
        raw_mx, raw_my, raw_mz = self.mag.get_mag()
        
        # Apply Calibration Offsets
        gx -= self.gyro_off_x
        gy -= self.gyro_off_y
        gz -= self.gyro_off_z
        
        # 2. Map Magnetometer Axes
        mx, my, mz = raw_my, raw_mx, -raw_mz
        
        # 3. Update the Mahony Filter
        # Note: Your MPU6500 class already scales gyro to degrees/sec, which Mahony requires.
        self.ahrs.update(gx, gy, gz, ax, ay, az, mx, my, mz)

        # 5. Retrieve and Convert Angles
        # invoke compute_angles() on demand and return radians.
        pitch_deg = math.degrees(self.ahrs.pitch)
        roll_deg = math.degrees(self.ahrs.roll)
        yaw_deg = math.degrees(self.ahrs.yaw)
        
        # Convert Pitch, Roll and Yaw to a continuous 0 to 180 degrees
        if abs(roll_deg) > 90:
            pitch_deg = -pitch_deg
        else:
            if pitch_deg >= 0:
                pitch_deg = pitch_deg - 180
            else:
                pitch_deg = pitch_deg + 180
        
        return pitch_deg, roll_deg, yaw_deg
    
    def center(self, delay):
        print("Finding Center")
        while True:
            #print((self.pitchoff, self.yawoff))
            self.pitchoff, self.rolloff, self.yawoff = self.get_orientation()
            if time.monotonic_ns() % delay < 5_000_000:
                break
        print("Done")
        
    def absmove(self, pitch, yaw):
        xin = (yaw - self.yawoff + 180) % 360 - 180
        yin = (pitch - self.pitchoff + 180) % 360 - 180
        
        x = np.interp(xin, [-self.inrange, self.inrange], [-self.outrangex, self.outrangex])[0]
        y = np.interp(yin, [-self.inrange, self.inrange], [-self.outrangey, self.outrangey])[0]
            
        x_value = int(x - self.xnot)
        y_value = int(y - self.ynot)
        
        self.m.move(-x_value, y_value)
        
        self.xnot = x
        self.ynot = y
        
        #print((x, y))
        #print((xnot, ynot))
        print((xin, yin))


m = Mouse(usb_hid.devices)
sen = busio.I2C(scl=board.GP15, sda=board.GP14, frequency=400000)
g = Gyro(i2c_bus = sen, mouse = m)

g.center(2_000_000_000) # 2s delay

print("Starting AHRS... Keep sensor still to allow filter to converge.")

last_update_time = time.monotonic_ns()
while True:
    current_time = time.monotonic_ns()
    
    if current_time - g.last_update_time >= g.UPDATE_INTERVAL_NS:
        pitch, roll, yaw = g.get_orientation()
        
        # Update the timer (don't forget this, or it runs as fast as possible!)
        g.last_update_time += g.UPDATE_INTERVAL_NS
        
        g.absmove(pitch, yaw)
