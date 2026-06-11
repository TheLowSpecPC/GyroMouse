import storage
import usb_hid

# Allows Internal Memory Access
storage.remount("/", readonly = False)