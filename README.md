# Project Skypiea ☁️🚢

**Project Skypiea** is a Python-based Ground Control Station (GCS) designed to command and monitor unmanned aerial vehicles (UAVs). Much like the mysterious Sky Island from One Piece, this project bridges the gap between the ground and the heavens, using **PyMavlink** to transmit "Dials" (commands) and telemetry data via hardware radio links.

---

## 🧭 Overview

This repository provides a streamlined interface to interact with flight controllers (ArduPilot/PX4). Whether you are looking to automate takeoffs, manage waypoints, or monitor real-time telemetry, **Project Skypiea** acts as your digital "Log Pose," guiding your drone through its mission.

### Key Features
* **Command & Control:** Remote arming, takeoff, landing, and mode switching.
* **Navigation:** Upload and manage complex mission waypoints.
* **Telemetry:** Real-time monitoring of EKF status, GPS, and system health.
* **Movement:** Precise control over velocity, yaw, and positioning.
* **Multi-Platform:** Support for both APM (ArduPilot) and PX4 flight stacks.

---

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Protocol:** [MAVLink](https://mavlink.io/en/)
* **Library:** [PyMavlink](https://github.com/ArduPilot/pymavlink)

---

## 🚀 Getting Started

### Prerequisites
Ensure you have Python installed and the necessary dependencies:
```bash
pip install -r requirements.txt
```

### Installation
1. Clone the "Sky Island":
   ```bash
   git clone https://github.com/AyushMaria/InstillGCS.git
   cd InstillGCS
   ```

### Usage
Connect your hardware GCS/Telemetry radio and run a script to interact with the drone. For example, to initiate a takeoff:
```bash
python takeoff.py
```

---

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| `APM.py` / `px4.py` | Stack-specific communication wrappers. |
| `movement.py` | Functions for guided movement and positioning. |
| `upload_waypoints.py` | Mission planning and waypoint injection. |
| `ekf_status.py` | Monitoring extended Kalman Filter health. |
| `listen.py` | Telemetry listener for real-time data logging. |

---

## ⚓ Lore & Inspiration

In the world of *One Piece*, **Skypiea** is a land beyond the clouds reachable only by those with the strongest will. 

* **The GCS:** Your "Dial" — the source of command and energy.
* **Telemetry:** Your "Mantra" (Observation Haki) — sensing the drone's position and state without seeing it.
* **The Drone:** Your "Ark Maxim" — a vessel designed to rule the skies.

---

## 🤝 Contributing

Contributions are welcome! If you find a bug or have a feature request (like adding support for "Wavers"), please open an issue or submit a pull request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.

*“The dreams of pirates will never end!” — Marshall D. Teech*
