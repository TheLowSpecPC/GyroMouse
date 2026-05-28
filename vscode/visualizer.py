import serial
from vpython import box, vector, rate, canvas, color

# --- CONFIGURATION ---
COM_PORT = 'COM7'  # Change this to your Pico W's serial port!
BAUD_RATE = 9600

# Open the serial connection
print(f"Connecting to {COM_PORT}...")
ser = serial.Serial(COM_PORT, BAUD_RATE)

# Set up the 3D scene
scene = canvas(title='Pico W AHRS Visualization', width=800, height=600)
scene.background = color.gray(0.2)

# Create our "Sensor" box
# X is Right/Left, Y is Up/Down, Z is Forward/Backward
sensor_box = box(length=5, width=3, height=1, color=color.cyan)

print("Waiting for data...")

while True:
    rate(100)  # Keep the loop running smoothly
    
    if ser.in_waiting:
        try:
            # Read a line from the Pico W and decode it
            line = ser.readline().decode('utf-8').strip()
            
            # Split the CSV string into 4 floating-point numbers
            q0, q1, q2, q3 = map(float, line.split(','))

            # ---------------------------------------------------------
            # THE MAGIC: Convert Quaternion to 3D Vectors
            # VPython needs an "Axis" (Forward direction) and 
            # an "Up" vector to know how to orient the box.
            # ---------------------------------------------------------
            
            # Calculate the Forward (X-axis) vector
            vx = 1.0 - 2.0 * (q2**2 + q3**2)
            vy = 2.0 * (q1 * q2 + q0 * q3)
            vz = 2.0 * (q1 * q3 - q0 * q2)

            # Calculate the Up (Y-axis) vector
            ux = 2.0 * (q1 * q2 - q0 * q3)
            uy = 1.0 - 2.0 * (q1**2 + q3**2)
            uz = 2.0 * (q2 * q3 + q0 * q1)

            # Apply the vectors to rotate the 3D box!
            sensor_box.axis = vector(vx, vy, vz)
            sensor_box.up = vector(ux, uy, uz)

        except Exception as e:
            # Ignore garbled lines that happen when you first connect
            pass