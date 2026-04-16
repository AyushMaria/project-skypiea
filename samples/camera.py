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




mav_connection = mavutil.mavlink_connection("127.0.0.1:14550")
		
# Initialising Drone Kit 	
vehicle = connect("127.0.0.1:14551", wait_ready=False)
print("Connected")

seen = set()
while True:
	msg = mav_connection.recv_match(blocking = True, timeout = 5)
	if msg:
		sys_id = msg.get_srcSystem()
		comp_id = msg.get_srcComponent()
		if (sys_id,comp_id) not in seen:
			seen.add((sys_id,comp_id))
			print(f"found {sys_id}, comp {comp_id},: {msg.get_type()}")

target_component = mavutil.mavlink.MAV_COMP_ID_CAMERA

mav_connection.mav.command_long_send(
	mav_connection.target_system,
	target_component,
	mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
	0,
	259,
	0,0,0,0,0,0
)

ack = mav_connection.recv_match(type='COMMAND_ACK', blocking = True)
if ack:
	print("Command Ack:", ack.to_dict())

cam_info = mav_connection.recv_match(type='CAMERA_INMFORMATION', blocking = True, timeout = 5)
if cam_info:
	print("Received CAMERA_INFORMATION:", cam_info.to_dict())
else:
	print("No Camera Found")
	

