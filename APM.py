from pymavlink import mavutil
from dronekit import connect, LocationGlobalRelative
import time
import argparse  
import keyboard
import evdev
import select

from utilities.connect_to_sysid import connect_to_sysid
from utilities.wait_for_position_aiding import wait_until_position_aiding
from utilities.get_autopilot_info import get_autopilot_info

main_mode_mapping_px4 = {
    'MANUAL': 0,
    'ALTCTL': 1,
    'POSCTL': 2,
    'AUTO': 3,
    'ACRO': 4,
    'OFFBOARD': 5,
    'STABILIZED': 6,
    'RATTITUDE': 7,
}

sub_mode_mapping_px4 = {
    'READY': 0,
    'TAKEOFF': 1,
    'HOLD': 2,  # LOITER in MAVLink
    'MISSION': 3,
    'RETURN_TO_LAUNCH': 4,
    'LAND': 5,
    'FOLLOW_ME': 6,
}

mode_px4_quad = {
    16: "ALTCTL",
    19: "HOLD",
    31: "STABILIZED",
    46: "RETURN_TO_LAUNCH"
}

mode_apm_quad = {
    16: "GUIDED",
    19: "LOITER",
    31: "STABILIZE",
    46: "RTL"
}

mode_apm_vtol = {
    21: "FBWB",
    22: "QSTABILIZE",
    17: "QHOVER",
    44: "Cruise",
    45: "FBWA",
    47: "QLOITER"
}

servo_on_apm = {
    33: "payload_drop",
    24: "weapon_launch"
}

servo_off_apm = {
    48: "payload_drop",
    25: "weapon_launch"
}

camera_commands = [
    18,
    35,
    38,
    23,
    30,
    32
]

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

DEBOUNCE_TIME = 0.2  # seconds to wait after last input before sending command
tgt_sys_id: int = 1

def takeoff(mav_connection, takeoff_altitude: float, tgt_sys_id: int = 1, tgt_comp_id=1):

    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))

    wait_until_position_aiding(mav_connection)
    autopilot_info = get_autopilot_info(mav_connection, tgt_sys_id)
    
    if autopilot_info["autopilot"] == "ardupilotmega":
        print("Connected to ArduPilot")
        mode_id = mav_connection.mode_mapping()["GUIDED"]
        takeoff_params = [0, 0, 0, 0, 0, 0, takeoff_altitude]

    elif autopilot_info["autopilot"] == "px4":
        print("Connected to PX4 autopilot")
        print(mav_connection.mode_mapping())
        mode_id = mav_connection.mode_mapping()["TAKEOFF"][1]
        print(mode_id)
        msg = mav_connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        starting_alt = msg.alt / 1000
        takeoff_params = [0, 0, 0, 0, float("NAN"), float("NAN"), starting_alt + takeoff_altitude]

    else:
        raise ValueError("Autopilot not supported")


    # Change mode to guided (Ardupilot) or takeoff (PX4)
    mav_connection.mav.command_long_send(tgt_sys_id, tgt_comp_id, mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                                0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id, 0, 0, 0, 0, 0)
    ack_msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
    print(f"Change Mode ACK:  {ack_msg}")

    # Arm the UAS
    mav_connection.mav.command_long_send(tgt_sys_id, tgt_comp_id,
                                         mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

    arm_msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
    print(f"Arm ACK:  {arm_msg}")

    # Command Takeoff
    mav_connection.mav.command_long_send(tgt_sys_id, tgt_comp_id,
                                         mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, takeoff_params[0], takeoff_params[1], takeoff_params[2], takeoff_params[3], takeoff_params[4], takeoff_params[5], takeoff_params[6])

    takeoff_msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
    print(f"Takeoff ACK:  {takeoff_msg}")

    return takeoff_msg.result


def arm(mav_connection):

    # Wait for the first heartbeat
    # This sets the system and component ID of remote system for the link
    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))

    mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

    msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True)
    print(msg)

    # return the result of the ACK message
    return msg.result
    
def disarm(mav_connection):

    # Wait for the first heartbeat
    # This sets the system and component ID of remote system for the link
    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))

    mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 0, 0, 0, 0, 0, 0)

    msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True)
    print(msg)

    # return the result of the ACK message
    return msg.result
    
def land(mav_connection, timeout: int = 10) -> int:
    """
    Sends a command for the drone to land.

    Args:
        the_connection (mavutil.mavlink_connection): The MAVLink connection to use.
        timeout (int): Time in seconds to wait for an acknowledgment.

    Returns:
        int: mavutil.mavlink.MAV_RESULT enum value.
    """

    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))
          
    	
    # Send a command to land
    mav_connection.mav.command_long_send(
        mav_connection.target_system, 
        mav_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND, 
        0, 0, 0, 0, 0, 0, 0, 0
    )

    # Wait for the acknowledgment
    ack = mav_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=timeout)
    if ack is None:
        print('No acknowledgment received within the timeout period.')
        return None

    return ack.result


def change_mode(mav_connection, mode, sub_mode):
	
    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))	
         
    #wait_until_position_aiding(mav_connection)
    autopilot_info = get_autopilot_info(mav_connection, tgt_sys_id)
    print(mode)
    if autopilot_info["autopilot"] == "ardupilotmega":
        # Check if mode is available
        if mode not in mav_connection.mode_mapping():
            print(f'Unknown mode : {mode}')
            print(f"available modes: {list(master.mode_mapping().keys())}")
            raise Exception('Unknown mode')
        
        # Get mode ID
        mode_id = mav_connection.mode_mapping()[mode]
        sub_mode = 0
    elif autopilot_info["autopilot"] == "px4":
        # Get mode ID
        mode_id = main_mode_mapping_px4[mode]
        sub_mode = sub_mode_mapping_px4[sub_mode]


    mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                                0, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id, sub_mode, 0, 0, 0, 0)
                                
    ack_msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
    
    if ack_msg is None:
        print('No acknowledgment received within the timeout period.')
        return None
    
    print(ack_msg)
    return ack_msg.result

def servo_on(mav_connection,servo_number):

    # Wait for the first heartbeat
    # This sets the system and component ID of remote system for the link
    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))

    mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0, servo_number, 1900, 0, 0, 0, 0, 0)

    msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True)
    print(msg)

    # return the result of the ACK message
    return msg.result
   
def servo_off(mav_connection,servo_number):

    # Wait for the first heartbeat
    # This sets the system and component ID of remote system for the link
    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))

    mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0, servo_number, 1100, 0, 0, 0, 0, 0)

    msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True)
    print(msg)

    # return the result of the ACK message
    return msg.result
    
def camera(mav_connection, code):

    # Wait for the first heartbeat
    # This sets the system and component ID of remote system for the link
    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))
    if code == 30:
    	# Start Video Capture
    	mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,2500, 0, 1, 0, 0, 0, 0, 0, 0)
    	msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True)
    	print(msg)
    elif code == 23:
    	# Stop Video Capture501, 0, 1, 0, 0, 0, 0, 0, 0)msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True)
    	print(msg)
    elif code == 38:
    	# Autofocus
    	mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         532, 0, 1, -1, 0, 0, 0, 0, 0)
    elif code == 35:
    	# Zoom in
    	mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         531, 0, 1, 1, 0, 0, 0, 0, 0)
    elif code == 32:
    	# Zoom Out
    	mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         531, 0, 1, -1, 0, 0, 0, 0, 0)
    elif code == 18:
    	# Click a picture
    	mav_connection.mav.command_long_send(mav_connection.target_system, mav_connection.target_component,
                                         2000, 0, 1, 0, 1, 0, 0, 0, 0)
    	
    msg = mav_connection.recv_match(type='COMMAND_ACK', blocking=True)
    print(msg)

    # return the result of the ACK message
    return msg.result


def goto_height(vehicle, target_height):

    # Wait for the first heartbeat
    # This sets the system and component ID of remote system for the link
    
    mav_connection.wait_heartbeat()
    print("Heartbeat from system (system %u component %u)" %
          (mav_connection.target_system, mav_connection.target_component))
    
    lat = vehicle.location.global_relative_frame.lat
    lon = vehicle.location.global_relative_frame.lon
    
    if lat is None or lon is None:
        print("Waiting for GPS fix before commanding altitude change...")
        return
    
    target_location = LocationGlobalRelative(lat, lon, target_height)
    print(f"Commanding vehicle to altitude {target_height} m relative to home.")
    
    vehicle.simple_goto(target_location)
    
    
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Send arm/disarm commands using MAVLink protocol.')
	parser.add_argument('-c', '--connect', help="Connection string", default='127.0.0.1:14550')
	parser.add_argument("--altitude", type=int, help="Altitude for the UAV to reach upon takeoff.", default=20)
	parser.add_argument("--sysid", type=int, help="System ID of the UAV to command.", default=1)
	parser.add_argument('--timeout', type=int, default=10, help='Timeout in seconds to wait for a command acknowledgment.')
	# parser.add_argument('-a', '--arm', type=int, choices=[0, 1], help="Arm/Disarm command", default=1)
    
	args = parser.parse_args()
	
	# Initialising PyMavlink
	mav_connection = mavutil.mavlink_connection(args.connect)
		
	# Initialising Drone Kit 	
	vehicle = connect("127.0.0.1:14551", wait_ready=False)
	print("Connected")
	devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
	
	camera_compid = 100
	
	msg_id = mavutil.mavlink.MAVLINK_MSG_ID_CAMERA_INFORMATION
	
	interval_us = 1_000_000
	
	mav_connection.mav.command_long_send(mav_connection.target_system,camera_compid,mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,0,msg_id,interval_us,0,0,0,0,0)
	
	msg = mav_connection.recv_match(type="CAMERA_INFORMATION", blocking=False)
	if msg:
		print(msg)
	else:
		print("NOPE")
	
	# determining device path 
	for x in devices:
		if x.name == "STMicroelectronics GENERIC_F446RCTX HID in FS Mode" and x.phys == "usb-0000:00:14.0-1.1/input1":
		#if x.name == "AT Translated Set 2 keyboard":
			device = x
			print(device)
			break
	
	
	# variables for height dial
	last_event_time = 0
	pending_altitude = None
	
	# pass ardupilot based values for existing event codes
	# if autopilot_info["autopilot"] == "ardupilotmega":
	while True:
		# Non-blocking: poll for new events, short timeout
		r, _, _ = select.select([device.fd], [], [], 0.05)
		if device.fd in r:
			for event in device.read(): 
				if event.type==1 and event.code == 50:
					result = arm(mav_connection)
					print(f'Result of arm command: {result}')
						
				elif event.type==1 and event.code == 49:
					result = disarm(mav_connection)
					print(f'Result of disarm command: {result}')
						
				elif event.type==1 and event.code == 34:
					result = takeoff(mav_connection, args.altitude)
					print(f'Result of takeoff command: {result}')
						
				elif event.type==1 and event.code == 37:
					result = land(mav_connection,args.timeout)
					print(f'Result of land command: {result}')
						
				elif event.type==1 and event.code in mode_apm_vtol:
					result =  change_mode(mav_connection, mode_apm_vtol[event.code], "READY")
					print(f'Result of mode change command: {result}')
						
				elif event.type==1 and event.code in mode_apm_quad:
					result =  change_mode(mav_connection, mode_apm_quad[event.code], "READY")
					print(f'Result of mode change command: {result}')
						
				elif event.type==1 and event.code == 33:
					result =  servo_on(mav_connection,9)
					print(f'Result of payload drop trigger command: {result}')
						
				elif event.type==1 and event.code in camera_commands:
					result =  camera(mav_connection, event.code)
					print(f'Result of camera trigger command: {result}')
					
				elif event.type==1 and event.code == 24:
					result =  servo_on(mav_connection,10)
					print(f'Result of weapon launch trigger command: {result}')
						
				elif event.type==1 and event.code == 25:
					result =  servo_off(mav_connection,10)
					print(f'Result of weapon launch trigger command: {result}')
					
				elif event.type==1 and event.code == 48:
					result =  servo_off(mav_connection,9)
					print(f'Result of payload servo command: {result}')
						
				elif event.type==1 and event.code in HEIGHT_MAP:
					pending_altitude = HEIGHT_MAP[event.code]
					last_event_time = time.time()
					print(f"Dial moved, pending altitude set to {pending_altitude}")

		# Debounce logic: send new altitude only after dial settles
		if pending_altitude is not None and (time.time() - last_event_time) > DEBOUNCE_TIME:
			goto_height(vehicle, pending_altitude)
			print(f"Altitude command sent: {pending_altitude}")
			pending_altitude = None
		time.sleep(0.01)
			
	
