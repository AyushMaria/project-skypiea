import asyncio
import time
import select
import evdev

from mavsdk import System, camera, action

# PX4 main mode mapping
mode_px4_quad = {
    16: "ALTCTL",
    19: "HOLD",
    31: "STABILIZED",
    46: "RETURN_TO_LAUNCH"
}

# Event codes for camera control
camera_commands = {
    30: "video_start",
    23: "video_stop",
    38: "autofocus",
    35: "zoom_in",
    32: "zoom_out",
    18: "photo"
}

HEIGHT_MAP = {
    2: 20,
    3: 30,
    4: 40,
    5: 50,
    6: 60,
    7: 70,
    8: 80,
    9: 90,
    10: 95,
    11: 100,
}

DEBOUNCE_TIME = 0.2  # seconds

# ================== PX4 ACTIONS ==================

async def px4_arm(drone):
    await drone.action.arm()  

async def px4_disarm(drone):
    await drone.action.disarm()

async def px4_takeoff(drone, altitude):
    await drone.action.set_takeoff_altitude(altitude)
    await drone.action.takeoff()

async def px4_land(drone):
    await drone.action.land()

async def px4_change_mode(drone, mode):
    from mavsdk.action_server import FlightMode
    mode_map = {
        "ALTCTL": FlightMode.ALTCTL,
        "STABILIZED": FlightMode.STABILIZED,
        "HOLD": FlightMode.HOLD,
        "RETURN_TO_LAUNCH": FlightMode.RETURN_TO_LAUNCH
    }
    if mode in mode_map:
        await drone.action_server.set_flight_mode(mode_map[mode])
        print(f"PX4 flight mode changed to {mode}")
    else:
        print(f"Unsupported PX4 mode: {mode}")

# Camera control
async def px4_camera_command(drone, cmd):
    
    from mavsdk.camera import (CameraError, Mode)
    
    if cmd == "video_start":    
        try:    
            await drone.camera.start_video()
        except CameraError as error:
            print(f"Couldn't take a photo with error: {error._result.result}")     
            
    elif cmd == "video_stop":
        try:
            await drone.camera.stop_video(component_id=1)
        except CameraError as error:
            print(f"Couldn't stop recording with error: {error._result.result}")
            
    #elif cmd == "autofocus":
    #    try:
    #        await drone.camera.focus(component_id=1)
    #    except CameraError as error:
    #        print(f"Couldn't autofocus with error: {error._result.result}")      
            
    elif cmd == "zoom_in":
        await drone.camera.zoom_in_start(component_id=1)
        await asyncio.sleep(1)
        await drone.camera.zoom_stop(component_id=1)
    
    elif cmd == "zoom_out":
        await drone.camera.zoom_out_start(component_id=1)
        await asyncio.sleep(1)
        await drone.camera.zoom_stop(component_id=1)
        
    elif cmd == "photo":
        print("Taking a photo")
        try:
            await drone.camera.take_photo(component_id=1)
        except CameraError as error:
            print(f"Couldn't take a photo with error: {error._result.result}")
        
# Servo control: PX4 needs MAVLink passthrough for this
async def px4_servo_on(drone, servo_num):
    # PX4 MAVSDK doesn't expose servo directly, would require MAVLink passthrough
    print(f"Servo {servo_num} ON - implement MAVLink passthrough if needed")

async def px4_servo_off(drone, servo_num):
    print(f"Servo {servo_num} OFF - implement MAVLink passthrough if needed")

# Goto height: keep current lat/lon, change altitude
async def px4_goto_height(drone, target_height):
    async for position in drone.telemetry.position():
        lat = position.latitude_deg
        lon = position.longitude_deg
        await drone.action.goto_location(lat, lon, target_height, position.absolute_altitude_m)
        print(f"Commanding drone to {target_height} m")
        break

# ================== MAIN LOOP ==================

async def main():
    drone = System()
    await drone.connect(system_address="udpin://127.0.0.1:14552")

    print("Waiting for PX4 connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("PX4 drone connected")
            break

    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    device = None
    for d in devices:
        if x.name == "STMicroelectronics GENERIC_F446RCTX HID in FS Mode" and x.phys == "usb-0000:00:14.0-1.1/input1":
        #if d.name == "AT Translated Set 2 keyboard":
            device = d
            break
    if not device:
        print("Device not found")
        return
    print(f"Using device: {device}")

    pending_altitude = None
    last_event_time = 0

    while True:
        r, _, _ = select.select([device.fd], [], [], 0.05)
        if device.fd in r:
            for event in device.read():
                if event.type != evdev.ecodes.EV_KEY or event.value != 1:
                    continue

                # Arm
                if event.code == 50:
                    print("-- Arming")
                    await px4_arm(drone)

                # Disarm
                elif event.code == 49:
                    print("-- Disarming")
                    await px4_disarm(drone)

                # Takeoff
                elif event.code == 34:
                    print("-- Taking Off") 
                    await px4_takeoff(drone, 20)

                # Land
                elif event.code == 37:
                    print("-- Landing")
                    await px4_land(drone)

                # Flight modes
                elif event.code in mode_px4_quad:
                    await px4_change_mode(drone, mode_px4_quad[event.code])

                # Camera commands
                elif event.code in camera_commands:
                    await px4_camera_command(drone, camera_commands[event.code])

                # Servo test
                elif event.code == 33:
                    print("Turning on payload servo") 
                    await px4_servo_on(drone, 9)
                elif event.code == 48:
                    print("Turning off payload servo")
                    await px4_servo_off(drone, 9)
                elif event.code == 24:
                    print("Turning on weapon servo")
                    await px4_servo_on(drone, 10)
                elif event.code == 25:
                    print("Turning off weapon servo")
                    await px4_servo_off(drone, 10)
                   
                # Height dial
                elif event.code in HEIGHT_MAP:
                    pending_altitude = HEIGHT_MAP[event.code]
                    last_event_time = time.time()
                    print(f"Dial moved, pending altitude = {pending_altitude}m")

        # Debounce for height change
        if pending_altitude is not None and (time.time() - last_event_time) > DEBOUNCE_TIME:
            await px4_goto_height(drone, pending_altitude)
            pending_altitude = None

if __name__ == "__main__":
    asyncio.run(main())