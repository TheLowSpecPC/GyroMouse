import board
import busio
import time
import mpu6500

# Initialize physical I2C pins
i2c_bus = busio.I2C(scl=board.GP15, sda=board.GP14)

# Instantiate your custom class
sensor = mpu6500.MPU6500(i2c_bus, address=0x68)

print("Sensor initialized successfully!")
print("-" * 40)

while True:
    # 1. Get Accelerometer Data
    accel_x, accel_y, accel_z = sensor.get_acceleration()
    print(f"Accel (g):   X: {accel_x:5.2f} | Y: {accel_y:5.2f} | Z: {accel_z:5.2f}")
    
    # 2. Get Gyroscope Data
    gyro_x, gyro_y, gyro_z = sensor.get_gyro()
    print(f"Gyro (dps):  X: {gyro_x} | Y: {gyro_y} | Z: {gyro_z}")
    
    # 3. Get Temperature Data
    temp_c = sensor.get_temperature()
    print(f"Temp (C):    {temp_c:5.2f}")
    
    print("-" * 40)
    time.sleep(0.1)
