# Project Skypiea ☁️

Hardware-linked Ground Control Station (GCS) that maps a custom USB HID controller to MAVLink commands for real-time UAV control on ArduPilot and PX4.

---

## Overview

Project Skypiea connects a physical STM32-based USB HID controller to a drone via `pymavlink`, translating hardware events into high-level flight commands such as arm/disarm, takeoff, landing, mode switching, camera triggering, servo actions, and altitude changes.[cite:3]  
The **main entry point is `key.py`**, which auto-detects the autopilot (ArduPilot or PX4) and runs the appropriate event loop.[cite:3]

All other Python files (except `APM.py`) are **sample scripts** that demonstrate how to execute specific commands by name using the same MAVLink patterns as `key.py`.[cite:3]  
`APM.py` is an **older, ArduPilot-focused version of `key.py`** kept for reference and backwards compatibility.[page:5]

---

## Key components

### `key.py` – main controller

`key.py` is the primary script you run in normal operation.[cite:3]

It:

- Connects to the flight controller via `pymavlink` and `dronekit`.[cite:3]
- Detects whether the target autopilot is **ArduPilot (`ardupilotmega`) or PX4** using `utilities.get_autopilot_info`.[cite:3]
- Listens to events from the custom HID controller via `evdev` and `select`.[cite:3]
- Maps specific key codes to:
  - Arm / disarm (`MAV_CMD_COMPONENT_ARM_DISARM`).[cite:3]
  - Takeoff (`MAV_CMD_NAV_TAKEOFF`) to a configurable altitude.[cite:3]
  - Land (`MAV_CMD_NAV_LAND`).[cite:3]
  - Mode changes (APM quad, APM VTOL, PX4 quad) via `MAV_CMD_DO_SET_MODE`.[cite:3]
  - Servo actions for payload drop and weapon launch via `MAV_CMD_DO_SET_SERVO`.[cite:3]
  - Camera video start via `MAV_CMD_VIDEO_START_CAPTURE`.[cite:3]
  - Altitude changes using a height dial mapped to discrete altitudes (20–100 m) through `dronekit.simple_goto`.[cite:3]

It keeps two separate loops:

- One for **ArduPilot**, using `mode_apm_quad` and `mode_apm_vtol` mappings.[cite:3]
- One for **PX4**, using `mode_px4_quad` plus submode mapping for actions like RETURN_TO_LAUNCH.[cite:3]

### `APM.py` – older version of `key.py`

`APM.py` contains an earlier design of the same concept and is primarily ArduPilot-oriented.[page:5]

It:

- Uses the same core functions (`takeoff`, `arm`, `disarm`, `land`, `change_mode`, `servo_on/off`, `goto_height`).[page:5]
- Implements a single ArduPilot-centric event loop instead of branching cleanly between ArduPilot and PX4.[page:5]
- Includes a more extensive **camera control block**, with key codes for start/stop video, autofocus, zoom in/out, and still pictures via raw MAV_CMD IDs.[page:5]
- Requests `CAMERA_INFORMATION` from a camera component as part of startup.[page:5]

You can treat `APM.py` as an **older, camera-heavy reference**; for new integrations and production use, prefer `key.py`.[cite:3][page:5]

### Sample scripts

All other Python files are **examples** that show how to call specific commands by name in isolation.[cite:3]  
They reuse the same connection logic and MAVLink patterns as `key.py`, but are focused on one operation per script.

Examples (non-exhaustive):[cite:3]

- `arm.py` – arm/disarm the vehicle.
- `takeoff.py` – perform a guided takeoff to a target altitude.
- `land.py` – send a landing command.
- `change_mode.py` – change flight modes.
- `movement.py` – send movement/guided navigation commands.
- `speed_yaw.py` – control speed and yaw.
- `upload_waypoints.py` – upload missions / waypoints.
- `ekf_status.py` – read and display EKF/position-aiding status.
- `listen.py`, `read.py` – telemetry listeners / message readers.
- `camera.py` – camera-related commands.
- `px4.py`, `APM.py` – autopilot-specific or legacy behavior examples.
- `dev.py`, `temp.py` – development/testing utilities.[cite:3]

Use these as **reference implementations** when you want to add new command mappings or understand how a specific MAVLink command is executed.

---

## Project structure

```text
project-skypiea/
├── key.py                # Main entry point: hardware HID → MAVLink bridge (APM + PX4)
├── APM.py                # Older ArduPilot-focused version of key.py (legacy/reference)
├── arm.py                # Example: arm/disarm
├── camera.py             # Example: camera commands
├── change_mode.py        # Example: change flight modes
├── dev.py                # Dev / debug utilities
├── eeprom.bin            # EEPROM dump (reference data)
├── ekf_status.py         # Example: EKF/position-aiding status
├── key.py                # Main script (repeated here for emphasis)
├── land.py               # Example: land command
├── listen.py             # Example: listen to MAVLink messages
├── mav.parm              # Saved parameter file
├── mav.tlog              # Telemetry log
├── mav.tlog.raw          # Raw telemetry log
├── movement.py           # Example: movement commands
├── px4.py                # Example: PX4-specific operations
├── read.py               # Example: read/display MAVLink messages
├── requirements.txt      # Python dependencies
├── speed_yaw.py          # Example: speed and yaw control
├── takeoff.py            # Example: takeoff
├── temp.py               # Scratch / experimental script
├── upload_waypoints.py   # Example: mission upload
├── logs/                 # Log storage
├── terrain/              # Terrain data
├── unittests/            # Unit tests
├── utilities/
│   ├── connect_to_sysid.py         # Helper: connect to specific sysid
│   ├── wait_for_position_aiding.py # Helper: wait for GPS/EKF readiness
│   └── get_autopilot_info.py       # Helper: detect autopilot type
└── wps/                  # Waypoint files
```

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/AyushMaria/project-skypiea.git
cd project-skypiea

pip install -r requirements.txt
pip install evdev dronekit
```

> `evdev` requires Linux and permission to read from `/dev/input` (usually root or adding the user to the `input` group).

---

## Usage

### Running the main controller

Make sure:

- The flight controller is powered and connected (serial port or UDP endpoint).
- The custom STM32 HID device is plugged in and visible under `/dev/input` with name `STMicroelectronics GENERIC_F446RCTX HID in FS Mode`.[cite:3]

Then run:

```bash
python key.py --connect 127.0.0.1:14550 --altitude 30 --sysid 1
```

Arguments:

| Flag | Default | Description |
| --- | --- | --- |
| `-c` / `--connect` | `127.0.0.1:14550` | MAVLink connection string (e.g. serial: `/dev/ttyUSB0`, UDP endpoint) |
| `--altitude` | `20` | Takeoff altitude in metres for the takeoff command |
| `--sysid` | `1` | MAVLink system ID of the target vehicle |
| `--timeout` | `10` | ACK timeout in seconds for critical commands |

`key.py` will:

- Autodetect ArduPilot vs PX4.
- Start the appropriate event loop.
- React to your hardware controller inputs by sending the mapped MAVLink commands.

---

## Command mappings (conceptual)

The HID input codes are mapped to operations such as:[cite:3][page:5]

- Arm / disarm.
- Takeoff to `--altitude`.
- Land.
- Mode changes (GUIDED/LOITER/STABILIZE/RTL for APM; ALTCTL/HOLD/STABILIZED/RTL for PX4).
- VTOL-specific modes via the APM VTOL map.
- Payload drop and weapon launch via servo channels.
- Camera trigger.
- Altitude changes based on a height dial (20–100 m) with debounce.

Refer to `key.py` if you want to adjust or extend key-to-command mappings.[cite:3]

---

## Dependencies

From `requirements.txt`:[cite:4]

- `pymavlink==2.4.39`
- `python-iq-sim==0.0.4`

Additionally (not in `requirements.txt` but required by the main script):[cite:3]

- `dronekit`
- `evdev`

---

## Notes

- Prefer **`key.py`** for all new development and operations.
- Treat **`APM.py`** as a legacy ArduPilot-specific version with extended camera control.
- Use the other Python files as **sample references** for scripting individual actions and testing specific commands.
