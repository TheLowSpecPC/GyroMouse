import board
import busio
import time
import sensor

# Initialize physical I2C pins
i2c_bus = busio.I2C(scl=board.GP15, sda=board.GP14)

# Instantiate your custom class
sen = sensor.MPU6500(i2c_bus)
mag = sensor.QMC5883L(i2c_bus)

print("Sensor initialized successfully!")
print("-" * 40)

while True:
    # 1. Get Accelerometer Data
    accel_x, accel_y, accel_z = sen.get_acceleration()
    print(f"Accel (g):   X: {accel_x:5.2f} | Y: {accel_y:5.2f} | Z: {accel_z:5.2f}")
    
    # 2. Get Gyroscope Data
    gyro_x, gyro_y, gyro_z = sen.get_gyro()
    print(f"Gyro (dps):  X: {gyro_x} | Y: {gyro_y} | Z: {gyro_z}")
    
    # 3. Get Magnatrometer Data
    mx, my, mz = mag.get_mag()
    print(f"Mag (idk):  X: {mx} | Y: {my} | Z: {mz}")
    
    # 4. Get Temperature Data
    temp_c = sen.get_temperature()
    print(f"Temp (C):    {temp_c:5.2f}")
    
    time.sleep(0.1)