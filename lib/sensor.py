import time
import struct

class MPU6500:
    def __init__(self, i2c_bus, address=0x68):
        self.i2c = i2c_bus
        self.address = address
        
        # MPU6500 Registers
        self.PWR_MGMT_1 = 0x6B
        self.ACCEL_XOUT_H = 0x3B
        self.TEMP_OUT_H = 0x41
        self.GYRO_XOUT_H = 0x43
        self.SMPLRT_DIV = 0x19
        self.CONFIG = 0x1A
        self.GYRO_CONFIG = 0x1B
        self.ACCEL_CONFIG = 0x1C
        
        # Wake up the sensor (write 0x00 to power management register)
        self._write_register(self.PWR_MGMT_1, 0x00)
        time.sleep(0.1) # Give it a moment to stabilize
        
        # Set Sample Rate Divider to 0 (Divider = 1 + SMPLRT_DIV)
        self._write_register(self.SMPLRT_DIV, 0x00)
        
        # Disable DLPF for max bandwidth (8kHz Gyro, 4kHz Accel)
        self._write_register(self.CONFIG, 0x00)
        
        # set Gyro Full Scale at ±1000dps
        self._write_register(self.GYRO_CONFIG, 0x10)
        self.dpscon = float(32750 / 1000)
        
        # set Accle Full Scale at ±8g
        self._write_register(self.ACCEL_CONFIG, 0x10)
        self.gcon = float(32768 / 8)

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
        
        # Default MPU6500 scale is ±2g (16384 LSB/g)
        return (ax / self.gcon, ay / self.gcon, az / self.gcon)

    def get_gyro(self):
        """Reads gyroscope data and returns (X, Y, Z) in degrees per second."""
        # Read 6 bytes starting from GYRO_XOUT_H
        data = self._read_registers(self.GYRO_XOUT_H, 6)
        
        # Unpack the 6 bytes into three 16-bit signed integers (>hhh)
        gx, gy, gz = struct.unpack('>hhh', data)
    
        # Default MPU6500 scale is ±250 dps (131 LSB/dps)
        return (gx / self.dpscon, gy / self.dpscon, gz / self.dpscon)

    def get_temperature(self):
        """Reads temperature data and returns degrees Celsius."""
        # Read 2 bytes starting from TEMP_OUT_H
        data = self._read_registers(self.TEMP_OUT_H, 2)
        
        # Unpack the 2 bytes into one 16-bit signed integer (>h)
        raw_temp = struct.unpack('>h', data)[0]
        
        # MPU6500 formula: (Raw / 333.87) + 21.0
        return (raw_temp / 333.87) + 21.0
    
    
class QMC5883L:
    def __init__(self, i2c_bus, address=0x0D): # QMC5883L default address is 0x0D
        self.i2c = i2c_bus
        self.address = address
        
        # QMC5883L specific startup sequence
        # 1. Write 0x01 to Set/Reset register (0x0B)
        self._write_register(0x0B, 0x01)
        
        # 2. Control Reg 1 (0x09): OSR=512, RNG=8G, ODR=200Hz, MODE=Continuous
        # 0x00 (OSR) | 0x10 (RNG) | 0x0C (ODR) | 0x01 (MODE) = 0x1D
        self._write_register(0x09, 0x1D) # Changed from 0x19 to 0x1D
        time.sleep(0.01)

    def _write_register(self, register, value):
        while not self.i2c.try_lock():
            pass
        try:
            self.i2c.writeto(self.address, bytes([register, value]))
        finally:
            self.i2c.unlock()

    def get_mag(self):
        # Read 6 bytes starting from X_LSB (0x00)
        buffer = bytearray(6)
        while not self.i2c.try_lock():
            pass
        try:
            self.i2c.writeto(self.address, bytes([0x00]))
            self.i2c.readfrom_into(self.address, buffer)
        finally:
            self.i2c.unlock()
            
        # Unpack as Little-Endian signed shorts (<hhh)
        mx, my, mz = struct.unpack('<hhh', buffer)
        return (mx, my, mz)