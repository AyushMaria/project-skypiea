import evdev
from select import select

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
print(devices)
for x in devices:
	#print(x.path, x.name, x.phys)
	if x.name == "STMicroelectronics GENERIC_F446RCTX HID in FS Mode" and x.phys == "usb-0000:00:14.0-1.1/input1":
		device = x
		break
# devices = {dev.fd: dev for dev in devices}

print(device)

for event in device.read_loop():
	print(event.type,event.code)
