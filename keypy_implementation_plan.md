# key.py Production Implementation Plan

## Goal

Refactor `key.py` from a single-file prototype into a production-ready hardware-to-MAVLink controller that is safer, more configurable, easier to test, and more reliable in real-world deployments.

***

## Current problems

The current implementation works as a functional prototype, but it has several limitations that reduce its reliability in field deployments:

- HID device name and physical path are hardcoded.
- DroneKit connects to a fixed endpoint (`127.0.0.1:14551`).
- Raw input event codes are embedded directly in long `if/elif` chains.
- ArduPilot logic, PX4 logic, hardware discovery, MAVLink command sending, and event dispatch all live in one file.
- Error handling is minimal.
- Blocking waits for ACKs can freeze the control loop.
- Several correctness issues exist in the current code path.

***

## Objectives

This implementation plan focuses on seven outcomes:

1. Improve flight safety.
2. Improve runtime reliability.
3. Make the system configurable across hardware and aircraft.
4. Refactor the code into maintainable modules.
5. Improve operator visibility and usability.
6. Fix correctness issues in the current implementation.
7. Add test and deployment infrastructure for production use.

***

## Phase 1 — Fix critical correctness issues

This phase should be completed before any structural refactor, because these issues can cause incorrect behavior during live operation.

### Tasks

- Fix `goto_height(vehicle, target_height)` so it does not reference `mav_connection` without receiving it explicitly.
- Fix the PX4 takeoff path where `takeoff(mav_connection, args.altitude, "ardupilot")` is currently called with the wrong autopilot identifier.
- Fix the PX4 event handler that calls `servo(mav_connection)` even though only `servo_on()` and `servo_off()` are defined.
- Normalize mode-handling logic so mode names and submodes are resolved through one tested translation layer instead of special-case string comparisons.
- Audit all event-code mappings to ensure every handler maps to an existing function.
- Add explicit checks for `None` ACK responses before using ACK objects.

### Deliverables

- A corrected `key.py` that no longer contains the known runtime bugs.
- A short regression checklist verifying arm, disarm, takeoff, land, mode change, servo, camera, and altitude commands.

***

## Phase 2 — Externalize configuration

Hardcoded values should be moved into a structured configuration file so the same codebase can support multiple remotes, aircraft, and deployment setups.

### Recommended config file

Use `config.yaml` for readability and future expansion.

### Config sections

#### Connection config

- MAVLink connection string
- DroneKit connection string
- Target system ID
- Target component ID
- ACK timeout
- Retry count

#### HID config

- Device name
- Vendor ID / Product ID (if available)
- Physical path
- Reconnect scan interval

#### Input mapping config

- Event code → action mapping
- Long-press actions
- Double-confirmation actions
- Emergency override action

#### Autopilot config

- ArduPilot mode mappings
- PX4 main mode mappings
- PX4 submode mappings
- Supported vehicle profiles

#### Actuator config

- Servo channel numbers
- PWM high/low values
- Camera action mappings
- Payload/actuator naming

#### Altitude config

- Height dial mapping
- Debounce time
- Min/max allowed altitude
- Altitude step size

### Deliverables

- `config.yaml`
- `config.py` for validation and loading
- Removal of hardcoded device paths, PWM values, and event-code logic from the main control loop

***

## Phase 3 — Add a safety layer

Critical actions should not be triggered directly from raw input events without validation.

### Safety rules to implement

- Allow `ARM` only if heartbeat is healthy and the vehicle is currently disarmed.
- Require GPS/EKF/position-aiding readiness before arming or takeoff.
- Reject takeoff if the current mode or autopilot state is incompatible.
- Add command cooldowns for land, RTL, servo actions, and camera triggers.
- Add long-press or two-step confirmation for dangerous actions.
- Add a highest-priority emergency action mapped to `LAND` or `RTL`.
- Validate target altitude against allowed min/max bounds.
- Prevent actuator commands unless the current state allows them.

### Recommended implementation

Create a command policy layer that evaluates:

- vehicle armed state
- current mode
- last heartbeat age
- GPS/EKF readiness
- altitude validity
- per-command cooldown window
- confirmation status for dangerous actions

### Deliverables

- `safety.py` or policy logic inside `actions.py`
- Cooldown registry
- Confirmation/guard logic for critical commands
- Emergency action support

***

## Phase 4 — Improve runtime reliability

The controller must survive disconnections and degraded conditions without silently failing.

### Reliability tasks

- Add heartbeat watchdog monitoring.
- Stop command dispatch if heartbeat is stale.
- Reconnect automatically if the MAVLink connection drops.
- Re-scan `/dev/input` if the HID disappears.
- Replace direct `recv_match(..., blocking=True)` usage with a reusable ACK helper.
- Add retry logic for command sending when appropriate.
- Return structured command results such as `SUCCESS`, `REJECTED`, `TIMEOUT`, `RETRYING`, and `FAILED`.
- Handle exceptions around device reads, serial disconnects, and MAVLink transport failures.

### Recommended helper abstraction

Create a generic helper such as:

```python
send_command_with_ack(...)
```

Responsibilities:

- send MAVLink command
- wait for ACK with timeout
- retry if allowed
- return a structured result object
- emit logs for each attempt

### Deliverables

- `mavlink_client.py` or equivalent helper module
- Heartbeat watchdog
- HID reconnect logic
- Structured ACK handling

***

## Phase 5 — Refactor into modules

`key.py` should become a thin entry point that wires together smaller modules.

### Proposed structure

```text
project-skypiea/
├── key.py                  # Thin startup entry point
├── controller.py           # Main runtime loop
├── input_adapter.py        # HID discovery, reading, normalization
├── dispatcher.py           # Event/action dispatch table
├── actions.py              # Arm, disarm, takeoff, land, mode, servo, camera, goto-height
├── autopilot.py            # APM/PX4 abstractions and mode translation
├── state.py                # Cached runtime state and health
├── config.py               # Config loading and validation
├── mavlink_client.py       # Command send/ACK/retry helpers
├── safety.py               # Command guardrails, cooldowns, confirmations
└── ui.py                   # Optional status dashboard / CLI output helpers
```

### Refactor principles

- Keep transport logic separate from control policy.
- Keep input normalization separate from action dispatch.
- Keep autopilot-specific logic behind a clean interface.
- Replace raw `if/elif` chains with a dispatch table.

### Dispatch table target design

Instead of:

```python
if event.code == 50:
    arm(...)
elif event.code == 49:
    disarm(...)
```

Move to:

```python
EVENT_ACTION_MAP = {
    50: "arm",
    49: "disarm",
    34: "takeoff",
}
```

Then resolve the action through a dispatcher that applies safety checks and command execution consistently.

### Deliverables

- New modular directory structure
- Thin `key.py`
- Event dispatcher with declarative mappings

***

## Phase 6 — Improve operator usability

The current script prints raw debug output, which is not enough for field operations.

### Operator-facing improvements

- Add structured logging with log levels.
- Use consistent command result messages: `SUCCESS`, `REJECTED`, `TIMEOUT`, `RETRYING`, `FAILED`.
- Print a startup summary showing autopilot type, sysid, HID status, active config, and available actions.
- Add colored CLI output for warnings and critical states.
- Add optional sound or visual confirmation for dangerous actions.
- Add a dry-run / simulation mode that accepts input events but does not transmit commands.
- Add a compact runtime status panel showing:
  - heartbeat status
  - connection health
  - autopilot type
  - mode
  - armed state
  - current altitude target
  - last command result

### Deliverables

- `--simulate` mode
- `--verbose` flag
- startup summary output
- structured logs in console and file

***

## Phase 7 — Add tests

A real-world controller should be testable without requiring live hardware every time.

### Test strategy

#### Unit tests

- Event code → action dispatch
- APM mode translation
- PX4 mode translation
- Altitude mapping and debounce behavior
- Safety rules and cooldown logic

#### Mocked command tests

- Arm command ACK handling
- Disarm command ACK handling
- Takeoff command ACK handling
- Land command ACK handling
- Servo command ACK handling
- Camera command ACK handling

#### Integration tests

- ArduPilot SITL flow
- PX4 SITL flow
- HID replay tests from recorded input traces

#### Regression tests

- Known bug tests for `goto_height`
- PX4 takeoff parameter test
- PX4 servo dispatch test

### Deliverables

- Expanded `unittests/`
- Mock transport layer for MAVLink testing
- SITL test scripts
- Recorded HID replay fixtures

***

## Phase 8 — Production deployment setup

For real use, the controller should run as a managed service rather than a manually launched script.

### Deployment tasks

- Add a `systemd` service file with auto-restart.
- Write logs to `logs/` using rotation.
- Support `--config`, `--simulate`, and `--verbose` CLI flags.
- Add `.env` or YAML-driven environment selection.
- Add release versioning and a changelog.
- Document startup and recovery procedures.

### Example service goals

- restart automatically on crash
- restart after transient serial/HID errors
- write operator-readable logs
- support safe shutdown on SIGTERM/SIGINT

### Deliverables

- `deploy/project-skypiea.service`
- log rotation setup
- updated README deployment section
- version/changelog workflow

***

## Recommended implementation order

If development time is limited, use this priority order:

1. Fix correctness bugs in the existing `key.py`.
2. Move hardcoded mappings and endpoints into `config.yaml`.
3. Replace raw `if/elif` event handling with a dispatch table.
4. Add safety guards, confirmations, and cooldowns.
5. Add heartbeat watchdog and reconnect logic.
6. Split the code into modules.
7. Add simulation mode and better operator logging.
8. Add unit tests, mock transport tests, and SITL coverage.
9. Package as a managed service with deployment assets.

***

## Suggested milestone breakdown

### Milestone 1 — Stabilize current script

- Fix current bugs
- Add safer ACK handling
- Add basic logging
- Add initial config file

### Milestone 2 — Make it configurable

- Move mappings to config
- Add dispatch table
- Separate autopilot logic

### Milestone 3 — Make it safe

- Add command guards
- Add cooldowns
- Add emergency override
- Add simulation mode

### Milestone 4 — Make it reliable

- Add watchdogs
- Add reconnect behavior
- Add structured results and retries

### Milestone 5 — Make it production-ready

- Modularize codebase
- Add test suite
- Add SITL automation
- Add deployment/service support

***

## Final target state

After implementation, the system should behave like a production controller service rather than a prototype script.

### Target characteristics

- Safe command execution with precondition checks
- Config-driven hardware and aircraft support
- Recoverable from HID and telemetry disconnects
- Clean separation of input, dispatch, autopilot logic, and transport
- Testable without physical hardware
- Usable by an operator with clear runtime visibility
- Deployable as a managed Linux service

***

## Recommended first coding task

Start by creating a branch for the refactor and implementing these four changes first:

1. Fix the three known code bugs.
2. Introduce `config.yaml`.
3. Add a small `send_command_with_ack()` helper.
4. Replace one section of the event loop with a dispatch table as a proof of concept.

That gives you a safe and incremental path without rewriting the whole controller at once.