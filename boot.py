import storage
import usb_hid
from absolute_mouse.descriptor import device as absolute_mouse_device

# Allows Internal Memory Access
storage.remount("/", readonly = False)

# Grab the default devices we still want (like Keyboard and Consumer Control)
# but leave out the standard Mouse.
enabled_devices = [
    usb_hid.Device.KEYBOARD,
    usb_hid.Device.MOUSE,
    usb_hid.Device.CONSUMER_CONTROL,
    absolute_mouse_device  # Add your custom absolute mouse
]

# Apply the custom USB configuration
usb_hid.enable(enabled_devices)