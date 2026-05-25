import time
import struct

class MPU6500:
    def __init__(self, i2c_bus, address=0x68):
        self.i2c = i2c_bus
        self.address = address
        
        # MPU6500 Registers
        self.PWR_MGMT_1 = 0x6B
        self.ACCEL_XOUT_H = 0x43
        self.TEMP_OUT_H = 0x41
        self.GYRO_XOUT_H =  0x3B
        
        # Wake up the sensor (write 0x00 to power management register)
        self._write_register(self.PWR_MGMT_1, 0x00)
        time.sleep(0.1) # Give it a moment to stabilize

    def _write_register(self, register, value):
        """Helper function to write a single byte to a register."""
        while not self.i2c.try_lock():
            pass
        try:
            self.i2c.writeto(self.address, bytes([register, value]))
        finally:
            self.i2c.unlock()

    def _read_registers(self, start_register, length):
        """Helper function to read multiple bytes from a starting register."""
        buffer = bytearray(length)
        while not self.i2c.try_lock():
            pass
        try:
            self.i2c.writeto(self.address, bytes([start_register]))
            self.i2c.readfrom_into(self.address, buffer)
        finally:
            self.i2c.unlock()
        return buffer

    def get_acceleration(self):
        """Reads accelerometer data and returns (X, Y, Z) in G-forces."""
        # Read 6 bytes starting from ACCEL_XOUT_H
        data = self._read_registers(self.ACCEL_XOUT_H, 6)
        
        # Unpack the 6 bytes into three 16-bit signed integers (>hhh)
        ax, ay, az = struct.unpack('>hhh', data)
        
        # Default MPU6500 scale is +/- 2g (16384 LSB/g)
        return (ax / 16384.0, ay / 16384.0, az / 16384.0)

    def get_gyro(self):
        """Reads gyroscope data and returns (X, Y, Z) in degrees per second."""
        # Read 6 bytes starting from GYRO_XOUT_H
        data = self._read_registers(self.GYRO_XOUT_H, 6)
        
        # Unpack the 6 bytes into three 16-bit signed integers (>hhh)
        gx, gy, gz = struct.unpack('>hhh', data)
        
        # Default MPU6500 scale is +/- 250 dps (131 LSB/dps)
        return (gx / 131.0, gy / 131.0, gz / 131.0)

    def get_temperature(self):
        """Reads temperature data and returns degrees Celsius."""
        # Read 2 bytes starting from TEMP_OUT_H
        data = self._read_registers(self.TEMP_OUT_H, 2)
        
        # Unpack the 2 bytes into one 16-bit signed integer (>h)
        raw_temp = struct.unpack('>h', data)[0]
        
        # MPU6500 formula: (Raw / 333.87) + 21.0
        return (raw_temp / 333.87) + 21.0