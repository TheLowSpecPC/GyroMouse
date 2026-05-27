import time
import board
import busio
from sensor import MPU6500, QMC5883L

i2c = busio.I2C(board.GP15, board.GP14, frequency=400000)
imu = MPU6500(i2c)
mag = QMC5883L(i2c)

def print_sensors():
    ax, ay, az = imu.get_acceleration()
    mx, my, mz = mag.get_mag()
    print("\n--- Current Reading ---")
    print(f"Accel -> X: {ax:6.2f} | Y: {ay:6.2f} | Z: {az:6.2f}")
    print(f"Mag   -> X: {mx:6.0f} | Y: {my:6.0f} | Z: {mz:6.0f}")

print("=== SENSOR ALIGNMENT TEST ===")
print("Gravity is your friend. An axis pointing straight UP against gravity will read around +1.00 G.")
print("The Earth's magnetic field is trickier, but we can look at the relative magnitudes.\n")

print("STEP 1: Place the board FLAT on the desk.")
print("Wait 3 seconds...")
time.sleep(3)
print_sensors()
print("-> Note which Accel axis reads ~ +1.00 or -1.00 (This is the Z-axis of the IMU).")
print("-> Note which Mag axis has the LARGEST absolute value.")
print("-" * 30)

print("\nSTEP 2: Stand the board UP vertically (pitch it up 90 degrees).")
print("Wait 5 seconds...")
time.sleep(5)
print_sensors()
print("-> Note which Accel axis reads ~ +1.00 or -1.00 (This is the X or Y axis of the IMU).")
print("-> Note which Mag axis just had a massive shift in value.")
print("-" * 30)

print("\nSTEP 3: Roll the board onto its SIDE (roll it 90 degrees).")
print("Wait 5 seconds...")
time.sleep(5)
print_sensors()
print("-> Note which Accel axis reads ~ +1.00 or -1.00 (This is the remaining axis).")
print("-> Note which Mag axis just changed.")
print("-" * 30)

print("\nTest Complete.")