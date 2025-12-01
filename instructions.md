# Line-by-Line Code Explanation

This document explains how the animatronic chatbot works, starting from execution and going through the code line by line.

---

## 🚀 Starting the Project

### `start_chatbot.sh` - Startup Script

```bash
#!/bin/bash
```

**Line 1**: This is a "shebang" that tells the system to use bash to execute this script.

```bash
cd /home/davidcr/chatbot
```

**Line 2**: Changes directory to the project folder. **Note**: You'll need to update this path to match your actual project location.

```bash
exec /home/davidcr/chatbot/cb-env/bin/python AIChatbot.py
```

**Line 3**:

-   `exec` replaces the current shell process with the Python interpreter
-   Runs Python from the virtual environment (`cb-env/bin/python`)
-   Executes `AIChatbot.py` as the main script
-   The virtual environment ensures all required packages are available

---

## 📝 `AIChatbot.py` - Main Application

### Section 1: Imports (Lines 1-22)

```python
import os
```

**Line 1**: Provides access to operating system interfaces (environment variables, file operations).

```python
import time
```

**Line 2**: Used for delays (`time.sleep()`) and timestamps (`time.time()`).

```python
import random
```

**Line 3**: Generates random numbers for eye movements, blink intervals, and idle phrases.

```python
import threading
```

**Line 4**: Allows multiple functions to run simultaneously (eyes, LED, idle speech in background threads).

```python
import wave
```

**Line 5**: Reads/writes WAV audio files.

```python
import pyaudio
```

**Line 6**: Handles audio input/output (microphone recording, speaker playback).

```python
import numpy as np
```

**Line 7**: Used for mathematical operations (logarithmic scaling of audio levels).

```python
import audioop
```

**Line 8**: Audio operations like calculating RMS (Root Mean Square) for volume detection.

```python
import subprocess
```

**Line 9**: Runs external commands (like `ffmpeg` to convert MP3 to WAV).

```python
import re
```

**Line 10**: Regular expressions for parsing emotion tags from AI responses.

```python
import digitalio
```

**Line 11**: Controls digital GPIO pins (button input, LED output).

```python
import sys
```

**Line 12**: System-specific parameters (checking if running in interactive terminal).

```python
# Load the .env file with the ChatGPT API key
from dotenv import load_dotenv
load_dotenv()
```

**Lines 14-16**:

-   Imports the function to load environment variables from `.env` file
-   `load_dotenv()` reads the `.env` file and makes `OPENAI_API_KEY` available via `os.getenv()`

```python
from openai import OpenAI, APIConnectionError
```

**Line 18**:

-   `OpenAI`: Main client for API calls (chat, TTS, transcription)
-   `APIConnectionError`: Exception type for network/connection failures

```python
import board
import busio
from adafruit_pca9685 import PCA9685
```

**Lines 20-22**:

-   `board`: Provides GPIO pin definitions (D13, D22, etc.)
-   `busio`: I2C communication interface
-   `PCA9685`: Driver for the 16-channel PWM servo controller

---

### Section 2: Platform Selection (Lines 24-29)

```python
# ================================================================
#  PLATFORM SELECTION
# ================================================================
# Set this to True if running on Raspberry Pi 5.
# Set to False for Raspberry Pi 4 (default).
USE_PI5 = True
```

**Lines 24-29**:

-   Flag to choose between Pi 4 and Pi 5 implementations
-   Pi 5 uses different Neopixel library (`adafruit-raspberry-pi5-neopixel`)
-   Pi 4 uses standard `adafruit-circuitpython-neopixel`
-   This affects how the mouth LEDs are controlled (see lines 146-180)

---

### Section 3: OpenAI Configuration (Lines 32-40)

```python
# ================================================================
#  OPENAI CONFIGURATION
# ================================================================

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**Line 36**:

-   Creates OpenAI client instance
-   `os.getenv("OPENAI_API_KEY")` retrieves the API key from environment (loaded from `.env`)

```python
CHAT_MODEL = "gpt-4.1-mini"
```

**Line 38**: Model used for conversational responses (note: this might be a typo - likely "gpt-4o-mini").

```python
TTS_MODEL = "gpt-4o-mini-tts"
```

**Line 39**: Model for text-to-speech conversion.

```python
VOICE_NAME = "echo"
```

**Line 40**: Voice style for TTS ("echo", "alloy", "fable", "onyx", "nova", "shimmer").

---

### Section 4: Audio Device Configuration (Lines 43-77)

```python
IDLE_PHRASES = [
    "Ready when you are.",
    "Anything I can help with?",
    "I'm here whenever you need me.",
    "Just say the word.",
    "How can I help?",
]
```

**Lines 47-53**: List of phrases the robot says after 90 seconds of silence (see `idle_speech_loop`).

```python
def find_audio_devices():
```

**Line 56**: Function to automatically detect USB microphone and speaker.

```python
    p = pyaudio.PyAudio()
```

**Line 57**: Creates PyAudio instance to query available audio devices.

```python
    input_index = None
    output_index = None
```

**Lines 58-59**: Variables to store device indices (will be `None` if not found).

```python
    for i in range(p.get_device_count()):
```

**Line 61**: Loops through all available audio devices.

```python
        info = p.get_device_info_by_index(i)
```

**Line 62**: Gets information about device at index `i`.

```python
        name = info.get("name", "").lower()
```

**Line 64**: Gets device name and converts to lowercase for case-insensitive matching.

```python
        # Find USB microphone
        if input_index is None and info.get("maxInputChannels") > 0:
```

**Line 67**:

-   Only looks if we haven't found an input device yet
-   Checks if device has input channels (microphone capability)

```python
            if "usb" in name or "mic" in name or "microphone" in name:
                input_index = i
```

**Lines 68-69**: If device name contains USB/mic keywords, saves its index.

```python
        # Find USB speaker
        if output_index is None and info.get("maxOutputChannels") > 0:
            if "usb" in name or "audio" in name or "speaker" in name:
                output_index = i
```

**Lines 71-74**: Same logic for output devices (speakers).

```python
    p.terminate()
    return input_index, output_index
```

**Lines 76-77**:

-   Closes PyAudio instance
-   Returns the found device indices (or `None` if not found)

---

### Section 5: Servo/Eye Configuration (Lines 80-137)

```python
i2c = busio.I2C(board.SCL, board.SDA)
```

**Line 84**:

-   Initializes I2C bus
-   `board.SCL` = Serial Clock line (GPIO3, Physical Pin 5)
-   `board.SDA` = Serial Data line (GPIO2, Physical Pin 3)

```python
pca = PCA9685(i2c)
```

**Line 85**: Creates PCA9685 servo driver instance connected via I2C.

```python
pca.frequency = 50
```

**Line 86**: Sets PWM frequency to 50 Hz (standard for servos).

```python
# Servo channel mapping
LEFT_X, LEFT_Y, LEFT_BLINK = 0, 1, 2
RIGHT_X, RIGHT_Y, RIGHT_BLINK = 3, 4, 5
```

**Lines 88-90**:

-   Defines which PCA9685 channels control which servos
-   Left eye: channels 0 (X), 1 (Y), 2 (blink)
-   Right eye: channels 3 (X), 4 (Y), 5 (blink)

```python
# Movement limits
X_LIMITS = (70, 110)
Y_LIMITS = (70, 110)
BLINK_LIMITS = (0, 40)
```

**Lines 92-95**:

-   `X_LIMITS`: Eye horizontal movement range (70-110 degrees)
-   `Y_LIMITS`: Eye vertical movement range (70-110 degrees)
-   `BLINK_LIMITS`: Eyelid range (0=open, 40=closed)

```python
# Servo directions
DIR_LEFT_X = 1
DIR_LEFT_Y = 1
DIR_LEFT_BLINK = 1

DIR_RIGHT_X = 1
DIR_RIGHT_Y = -1
DIR_RIGHT_BLINK = -1
```

**Lines 97-104**:

-   Direction multipliers (1 = normal, -1 = inverted)
-   Some servos may be mounted backwards, so direction is inverted
-   Right Y and blink are inverted

```python
# Blink configuration
BLINK_OPEN_LEFT = -12
BLINK_OPEN_RIGHT = 0
BLINK_SIDE_DELAY = 0.07
```

**Lines 106-109**:

-   `BLINK_OPEN_LEFT/RIGHT`: Trim values for "fully open" position (can be negative for over-travel)
-   `BLINK_SIDE_DELAY`: Time delay between left and right eyelid closing (creates staggered blink effect)

```python
MOVE_STEP = 1
MOVE_DELAY = 0.01
BLINK_INTERVAL = (7, 12)
BLINK_SPEED = 0.003
BLINK_HOLD = 0.10
```

**Lines 111-115**:

-   `MOVE_STEP`: Degrees to move per step (1 = smooth, larger = faster)
-   `MOVE_DELAY`: Delay between movement steps (0.01s = smooth animation)
-   `BLINK_INTERVAL`: Random time between blinks (7-12 seconds)
-   `BLINK_SPEED`: Time per blink step (0.003s = fast blink)
-   `BLINK_HOLD`: How long eyes stay closed during blink (0.10s)

```python
last_blink_timestamp = 0.0
```

**Line 117**: Tracks when last blink occurred (prevents overlapping blinks).

```python
# Servo pulse widths
MIN_PULSE_MS = 0.5
MAX_PULSE_MS = 2.5
PERIOD_MS = 20.0
```

**Lines 119-122**:

-   Standard servo PWM parameters
-   Pulse width: 0.5ms (0°) to 2.5ms (180°)
-   Period: 20ms (50 Hz)

```python
# Mouth smoothing factor
MOUTH_SMOOTHING = 0.6  # 0 = jumpy, 1 = smooth
previous_audio_level = 0.0
```

**Lines 124-126**:

-   `MOUTH_SMOOTHING`: How much to blend current audio level with previous (0.6 = 60% old, 40% new)
-   `previous_audio_level`: Stores last audio level for smoothing

```python
# Global state flags
is_running = True
is_speaking = False
is_thinking = False
is_armed = False  # True when button is ON (pressed), False when OFF
is_offline = False  # True when OpenAI can't be reached
```

**Lines 128-134**:

-   `is_running`: Main loop flag (set to `False` to exit)
-   `is_speaking`: True when TTS is playing
-   `is_thinking`: True when processing user input
-   `is_armed`: True when button is pressed (system active)
-   `is_offline`: True when internet connection fails

```python
# Track servo angles
current_servo_angles = {}
```

**Lines 136-137**: Dictionary storing current angle of each servo (for smooth movement calculations).

---

### Section 6: Neopixel Mouth Configuration (Lines 140-208)

```python
NEOPIXEL_PIN = board.D13
NUM_PIXELS = 8
```

**Lines 143-144**:

-   GPIO pin for Neopixel data line (GPIO13, Physical Pin 33)
-   Number of LEDs in the mouth strip

```python
if USE_PI5:
```

**Line 146**: Conditional block for Raspberry Pi 5 implementation.

```python
    # ------------------------------------------------------------
    # Raspberry Pi 5 implementation
    # ------------------------------------------------------------
    import adafruit_pixelbuf
    from adafruit_raspberry_pi5_neopixel_write import neopixel_write
```

**Lines 147-151**:

-   Imports Pi 5-specific Neopixel library
-   Pi 5 uses different low-level driver

```python
    class Pi5PixelBuf(adafruit_pixelbuf.PixelBuf):
        """Custom PixelBuf implementation for Raspberry Pi 5."""

        def __init__(self, pin, size, **kwargs):
            self._pin = pin
            super().__init__(size=size, **kwargs)

        def _transmit(self, buf):
            neopixel_write(self._pin, buf)
```

**Lines 153-161**:

-   Custom class that extends `PixelBuf`
-   `__init__`: Stores pin number, calls parent constructor
-   `_transmit`: Called when pixels need updating, uses Pi 5-specific write function

```python
    pixels = Pi5PixelBuf(
        NEOPIXEL_PIN,
        NUM_PIXELS,
        auto_write=True,
        byteorder="BRG",
    )
```

**Lines 163-168**:

-   Creates Neopixel instance for Pi 5
-   `auto_write=True`: Updates LEDs immediately when values change
-   `byteorder="BRG"`: Color order (Blue-Red-Green) - adjust if colors look wrong

```python
else:
    # ------------------------------------------------------------
    # Raspberry Pi 4 implementation
    # ------------------------------------------------------------
    import neopixel
    pixels = neopixel.NeoPixel(
        NEOPIXEL_PIN,
        NUM_PIXELS,
        auto_write=True,
        pixel_order=neopixel.GRB,   # change if colors look off
    )
```

**Lines 170-180**:

-   Pi 4 uses standard `neopixel` library
-   `pixel_order=neopixel.GRB`: Different color order for Pi 4

```python
def show_mouth(amplitude, color=(256, 256, 256)):
```

**Line 183**: Function to display mouth animation based on audio amplitude.

```python
    """Display mouth levels symmetrically based on amplitude."""
    amplitude = max(0.0, min(1.0, amplitude))
```

**Lines 184-185**:

-   Clamps amplitude between 0.0 and 1.0 (prevents invalid values)

```python
    num_lit = int(round(amplitude * NUM_PIXELS))
```

**Line 186**: Calculates how many LEDs should be lit (0-8 based on amplitude).

```python
    pixels.fill((0, 0, 0))
```

**Line 188**: Turns off all LEDs first.

```python
    center_left = NUM_PIXELS // 2 - 1
    center_right = NUM_PIXELS // 2
```

**Lines 190-191**:

-   Finds center LEDs (for 8 pixels: left=3, right=4)
-   Creates symmetric display from center outward

```python
    for i in range(num_lit // 2):
```

**Line 193**: Loops for half the lit LEDs (since we light both sides).

```python
        left_pos = center_left - i
        right_pos = center_right + i
```

**Lines 194-195**: Calculates positions moving outward from center.

```python
        if 0 <= left_pos < NUM_PIXELS:
            pixels[left_pos] = color
        if 0 <= right_pos < NUM_PIXELS:
            pixels[right_pos] = color
```

**Lines 197-200**:

-   Checks bounds (prevents array errors)
-   Sets LED color at calculated positions

```python
    pixels.show()
```

**Line 202**: Updates physical LEDs (if `auto_write=False`, this would be needed).

```python
def clear_mouth():
    """Turn off all mouth LEDs."""
    pixels.fill((0, 0, 0))
    pixels.show()
```

**Lines 205-208**: Utility function to turn off all mouth LEDs.

---

### Section 7: Button and LED Setup (Lines 211-228)

```python
# We'll use GPIO22 for the button, GPIO23 for the LED
BUTTON_PIN = board.D22   # Physical pin 15
LISTEN_LED_PIN = board.D23  # Physical pin 16
```

**Lines 215-217**: Defines GPIO pins for button and status LED.

```python
# Button: input with pull-up, pressed when pulled to GND
listen_button = digitalio.DigitalInOut(BUTTON_PIN)
listen_button.direction = digitalio.Direction.INPUT
listen_button.pull = digitalio.Pull.UP  # not pressed = True, pressed = False
```

**Lines 219-222**:

-   Creates digital I/O object for button
-   Sets as input
-   Enables internal pull-up resistor
-   When button pressed (connected to GND), `value` becomes `False`
-   When not pressed, `value` is `True`

```python
# LED: output, off by default
listen_led = digitalio.DigitalInOut(LISTEN_LED_PIN)
listen_led.direction = digitalio.Direction.OUTPUT
listen_led.value = False
```

**Lines 224-227**:

-   Creates digital I/O object for LED
-   Sets as output
-   Initializes to `False` (LED off)

---

### Section 8: Servo Control Functions (Lines 230-473)

```python
def set_servo_angle(channel, direction, angle):
```

**Line 234**: Function to set a single servo to a specific angle.

```python
    """Send corrected angle to PCA9685 servo."""
    if direction == -1:
        angle = 180 - angle
```

**Lines 235-237**:

-   If direction is inverted (-1), flips the angle
-   Example: 90° becomes 90° if direction=1, but becomes 90° if direction=-1 (no change)
-   Actually: 0° becomes 180°, 180° becomes 0° (inverted)

```python
    pulse_range = MAX_PULSE_MS - MIN_PULSE_MS
    pulse_width = MIN_PULSE_MS + (pulse_range * angle / 180.0)
```

**Lines 239-240**:

-   Calculates pulse width in milliseconds
-   Maps 0-180° angle to 0.5-2.5ms pulse width
-   Formula: `pulse_width = 0.5 + (2.0 * angle / 180.0)`

```python
    duty_cycle = int((pulse_width / PERIOD_MS) * 65535)
```

**Line 241**:

-   Converts pulse width to duty cycle (0-65535 for 16-bit PWM)
-   Formula: `duty_cycle = (pulse_width / 20.0) * 65535`

```python
    pca.channels[channel].duty_cycle = duty_cycle
```

**Line 243**: Sends PWM signal to specified servo channel.

```python
def move_servos_together(angle_targets, current_angles):
```

**Line 246**: Function to smoothly move multiple servos simultaneously.

```python
    """Smoothly move several servos together."""
    max_steps = 0
    for ch, (_, target) in angle_targets.items():
        max_steps = max(max_steps, abs(target - current_angles.get(ch, target)))
```

**Lines 247-250**:

-   Finds the servo that needs to move the most
-   `max_steps` = maximum angle difference across all servos
-   This ensures all servos finish moving at the same time

```python
    if max_steps == 0:
        return
```

**Lines 252-253**: Early exit if no movement needed.

```python
    for step in range(0, max_steps + 1, MOVE_STEP):
```

**Line 255**: Loops through movement steps (0 to max_steps, incrementing by MOVE_STEP).

```python
        for ch, (direction, target) in angle_targets.items():
            start = current_angles.get(ch, target)
            if start == target:
                continue
```

**Lines 256-259**:

-   Loops through each servo channel
-   Gets starting angle (or uses target if not in dictionary)
-   Skips if already at target

```python
            t = min(1.0, step / max_steps)
            new_angle = int(start + (target - start) * t)
```

**Lines 261-262**:

-   `t` = interpolation factor (0.0 to 1.0)
-   Calculates intermediate angle using linear interpolation
-   Example: start=70, target=90, step=10, max_steps=20 → t=0.5 → new_angle=80

```python
            set_servo_angle(ch, direction, new_angle)
```

**Line 264**: Sets servo to interpolated angle.

```python
        time.sleep(MOVE_DELAY)
```

**Line 266**: Small delay between steps (creates smooth animation).

```python
    for ch, (_, target) in angle_targets.items():
        current_angles[ch] = target
```

**Lines 268-269**: Updates current_angles dictionary to final positions.

```python
def random_eye_position(scale=1.0):
```

**Line 272**: Generates random eye coordinates within limits.

```python
    """Generate random eye coordinates."""
    x_mid = (X_LIMITS[0] + X_LIMITS[1]) // 2
    y_mid = (Y_LIMITS[0] + Y_LIMITS[1]) // 2
```

**Lines 273-275**: Calculates center point of movement range.

```python
    x_radius = int((X_LIMITS[1] - X_LIMITS[0]) / 2 * scale)
    y_radius = int((Y_LIMITS[1] - Y_LIMITS[0]) / 2 * scale)
```

**Lines 277-278**:

-   Calculates radius of movement (half the range)
-   `scale` parameter allows smaller movements (0.5 = half range, 1.0 = full range)

```python
    x = random.randint(x_mid - x_radius, x_mid + x_radius)
    y = random.randint(y_mid - y_radius, y_mid + y_radius)
```

**Lines 280-281**: Generates random coordinates within the scaled radius.

```python
    return x, y
```

**Line 283**: Returns random (x, y) coordinates.

```python
def blink_eyes(probability=1.0):
```

**Line 286**: Performs a natural blink with staggered eyelid motion.

```python
    """Full natural blink with staggered eyelid motion."""
    global is_armed
    if not is_armed:
        return
```

**Lines 287-290**:

-   Only blinks if system is armed (button on)
-   Prevents blinking when sleeping

```python
    if random.random() > probability:
        return
```

**Lines 292-293**: Random chance to skip blink (if probability < 1.0).

```python
    left_open = BLINK_OPEN_LEFT
    right_open = BLINK_OPEN_RIGHT
    closed = BLINK_LIMITS[1]
```

**Lines 295-297**: Gets open and closed positions for both eyelids.

```python
    left_range = closed - left_open
    right_range = closed - right_open
```

**Lines 299-300**: Calculates total movement range for each eyelid.

```python
    steps_total = max(left_range, right_range)
    if steps_total <= 0:
        return
```

**Lines 302-304**:

-   Uses the larger range to determine total steps
-   Early exit if invalid

```python
    side_offset_steps = int(round(BLINK_SIDE_DELAY / BLINK_SPEED))
```

**Line 306**: Converts time delay into step count (how many steps to delay right eye).

```python
    # Closing motion
    for step in range(0, steps_total + 1):
```

**Lines 308-309**: Loops through closing phase.

```python
        left_progress = min(step, left_range) / left_range if left_range > 0 else 1.0

        right_step_corrected = max(0, step - side_offset_steps)
        right_progress = min(right_step_corrected, right_range) / right_range if right_range > 0 else 1.0
```

**Lines 310-313**:

-   Calculates progress (0.0 to 1.0) for each eyelid
-   Right eye is delayed by `side_offset_steps`
-   Creates staggered blink effect (left closes slightly before right)

```python
        left_angle = int(left_open + left_progress * left_range)
        right_angle = int(right_open + right_progress * right_range)
```

**Lines 315-316**: Calculates current angle for each eyelid.

```python
        set_servo_angle(LEFT_BLINK, DIR_LEFT_BLINK, left_angle)
        set_servo_angle(RIGHT_BLINK, DIR_RIGHT_BLINK, right_angle)

        time.sleep(BLINK_SPEED)
```

**Lines 318-321**:

-   Sets servo positions
-   Small delay creates smooth motion

```python
    time.sleep(BLINK_HOLD)
```

**Line 323**: Holds eyes closed briefly.

```python
    # Opening motion
    for step in range(steps_total, -1, -1):
```

**Lines 325-326**: Loops backwards through opening phase (same logic as closing).

```python
        left_progress = min(step, left_range) / left_range if left_range > 0 else 1.0

        right_step_corrected = max(0, step - side_offset_steps)
        right_progress = min(right_step_corrected, right_range) / right_range if right_range > 0 else 1.0

        left_angle = int(left_open + left_progress * left_range)
        right_angle = int(right_open + right_progress * right_range)

        set_servo_angle(LEFT_BLINK, DIR_LEFT_BLINK, left_angle)
        set_servo_angle(RIGHT_BLINK, DIR_RIGHT_BLINK, right_angle)

        time.sleep(BLINK_SPEED)
```

**Lines 327-338**: Same logic as closing, but in reverse (eyes open).

```python
def wink():
```

**Line 341**: Performs a single-eye wink (random left or right).

```python
    """Random single-eye wink."""

    global last_blink_timestamp, is_armed
    if not is_armed:
        return

    last_blink_timestamp = time.time()
    chosen_side = random.choice(["left", "right"])
```

**Lines 343-349**:

-   Updates blink timestamp
-   Randomly chooses which eye to wink

```python
    left_open = BLINK_OPEN_LEFT
    right_open = BLINK_OPEN_RIGHT
    closed = BLINK_LIMITS[1]

    steps = abs(closed - left_open)
```

**Lines 351-354**: Gets positions and calculates steps needed.

```python
    # LEFT wink
    if chosen_side == "left":
        for step in range(steps + 1):
            angle = int(left_open + (closed - left_open) * (step / steps))
            set_servo_angle(LEFT_BLINK, DIR_LEFT_BLINK, angle)
            time.sleep(BLINK_SPEED)

        time.sleep(BLINK_HOLD)

        for step in range(steps, -1, -1):
            angle = int(left_open + (closed - left_open) * (step / steps))
            set_servo_angle(LEFT_BLINK, DIR_LEFT_BLINK, angle)
            time.sleep(BLINK_SPEED)
```

**Lines 356-369**:

-   Closes left eyelid
-   Holds closed
-   Opens left eyelid
-   Right eye stays open

```python
    else:  # RIGHT wink
        for step in range(steps + 1):
            angle = int(right_open + (closed - right_open) * (step / steps))
            set_servo_angle(RIGHT_BLINK, DIR_RIGHT_BLINK, angle)
            time.sleep(BLINK_SPEED)

        time.sleep(BLINK_HOLD)

        for step in range(steps, -1, -1):
            angle = int(right_open + (closed - right_open) * (step / steps))
            set_servo_angle(RIGHT_BLINK, DIR_RIGHT_BLINK, angle)
            time.sleep(BLINK_SPEED)
```

**Lines 371-382**: Same logic for right eye wink.

```python
    last_blink_timestamp = time.time()
```

**Line 384**: Updates timestamp after wink completes.

```python
def blink_twice():
    """Double blink."""
    global last_blink_timestamp, is_armed
    if not is_armed:
        return

    for _ in range(2):
        blink_eyes(probability=1.0)
        last_blink_timestamp = time.time()
        time.sleep(0.3)
```

**Lines 387-396**:

-   Performs two full blinks in sequence
-   0.3 second pause between blinks

---

### Section 9: Background Thread Functions (Lines 399-530)

```python
def eyes_idle_loop():
```

**Line 399**: Background thread function for continuous eye movement.

```python
    """Background idle movement and blinking for eyes."""
    global is_running, is_speaking, is_thinking, last_blink_timestamp, is_armed, is_offline

    next_blink = time.time() + random.uniform(*BLINK_INTERVAL)
```

**Lines 400-403**:

-   Accesses global state variables
-   Calculates when next automatic blink should occur

```python
    while is_running:
```

**Line 405**: Main loop (runs until `is_running = False`).

```python
        # If no internet, hold the offline pose (set_offline_face already did it)
        if is_offline:
            time.sleep(0.1)
            continue
```

**Lines 407-410**:

-   If offline, just wait (offline pose already set)
-   Prevents eye movement during offline state

```python
        if not is_armed:
            time.sleep(0.1)
            continue
```

**Lines 412-414**:

-   If button off (sleeping), just wait
-   Eyes don't move when sleeping

```python
        now = time.time()

        # THINKING MODE
        if is_thinking:
```

**Lines 416-418**: Gets current time, checks if in thinking mode.

```python
            for _ in range(2):
                new_x, new_y = random_eye_position(scale=0.5)
                targets = {
                    LEFT_X: (DIR_LEFT_X, new_x),
                    LEFT_Y: (DIR_LEFT_Y, new_y),
                    RIGHT_X: (DIR_RIGHT_X, new_x),
                    RIGHT_Y: (DIR_RIGHT_Y, new_y)
                }

                move_servos_together(targets, current_servo_angles)

                if random.random() < 0.3 and now - last_blink_timestamp > 0.2:
                    blink_eyes(probability=1.0)
                    last_blink_timestamp = time.time()

                time.sleep(1)
```

**Lines 419-435**:

-   Thinking mode: smaller eye movements (scale=0.5)
-   Moves eyes twice
-   30% chance to blink (if enough time since last blink)
-   1 second pause between movements

```python
        # SPEAKING MODE
        elif is_speaking:
            new_x, new_y = random_eye_position(scale=0.3)
            targets = {
                LEFT_X: (DIR_LEFT_X, new_x),
                LEFT_Y: (DIR_LEFT_Y, new_y),
                RIGHT_X: (DIR_RIGHT_X, new_x),
                RIGHT_Y: (DIR_RIGHT_Y, new_y)
            }

            move_servos_together(targets, current_servo_angles)

            if random.random() < 0.2 and now - last_blink_timestamp > 0.2:
                blink_eyes(probability=1.0)
                last_blink_timestamp = time.time()

            time.sleep(random.uniform(0.8, 1.8))
```

**Lines 437-453**:

-   Speaking mode: very subtle movements (scale=0.3)
-   20% chance to blink
-   Random pause (0.8-1.8 seconds)

```python
        # IDLE MODE
        else:
            new_x, new_y = random_eye_position(scale=1.0)
            targets = {
                LEFT_X: (DIR_LEFT_X, new_x),
                LEFT_Y: (DIR_LEFT_Y, new_y),
                RIGHT_X: (DIR_RIGHT_X, new_x),
                RIGHT_Y: (DIR_RIGHT_Y, new_y)
            }

            move_servos_together(targets, current_servo_angles)

            if now >= next_blink:
                blink_eyes(probability=1.0)
                last_blink_timestamp = time.time()
                next_blink = time.time() + random.uniform(*BLINK_INTERVAL)

            time.sleep(random.uniform(1, 3))
```

**Lines 455-472**:

-   Idle mode: full range movements (scale=1.0)
-   Checks if it's time for automatic blink
-   Random pause (1-3 seconds)

```python
def led_blink_loop():
```

**Line 475**: Background thread for status LED control.

```python
    """
    LED behavior:
    - OFF if not armed
    - BLINK when busy (thinking or speaking)
    - SOLID ON when ready for input
    """
    global is_running, is_thinking, is_speaking, listen_led, is_armed

    while is_running:
```

**Lines 476-484**:

-   Documentation of LED states
-   Main loop

```python
        if not is_armed:
            listen_led.value = False
            time.sleep(0.1)
            continue
```

**Lines 485-488**: LED off when button off.

```python
        # Busy (cannot accept input): blink
        if is_thinking or is_speaking:
            listen_led.value = True
            time.sleep(0.3)
            listen_led.value = False
            time.sleep(0.3)
            continue
```

**Lines 490-496**:

-   Blinks LED when busy (thinking or speaking)
-   0.3s on, 0.3s off

```python
        # Ready: solid ON
        listen_led.value = True
        time.sleep(0.1)
```

**Lines 498-500**: LED solid on when ready to listen.

```python
def idle_speech_loop():
```

**Line 503**: Background thread for idle speech.

```python
    global is_running, is_speaking, is_thinking, is_armed

    last_spoke_time = time.time()
    IDLE_INTERVAL = 90   # seconds of silence before it talks (adjust here)
```

**Lines 504-507**:

-   Tracks when last speech occurred
-   90 second timeout

```python
    while is_running:
        time.sleep(1)

        # Do NOT speak while the bot is:
        # - Sleeping (switch off)
        # - Thinking
        # - Speaking
        if not is_armed:
            last_spoke_time = time.time()
            continue

        if is_thinking or is_speaking:
            last_spoke_time = time.time()
            continue
```

**Lines 509-522**:

-   Checks every second
-   Resets timer if sleeping, thinking, or speaking
-   Prevents interrupting active conversation

```python
        # If too much quiet time passes, say an idle phrase
        if time.time() - last_spoke_time > IDLE_INTERVAL:
            phrase = random.choice(IDLE_PHRASES)
            print(f"[Idle message] {phrase}")
            speak_text(phrase, color=(0, 255, 0))
            last_spoke_time = time.time()
```

**Lines 524-528**:

-   If 90 seconds of silence, picks random idle phrase
-   Speaks it with green color
-   Resets timer

---

### Section 10: Eye Positioning Functions (Lines 532-619)

```python
def center_eyes():
    """Move eyes and eyelids to neutral center positions."""
    neutral_x = (X_LIMITS[0] + X_LIMITS[1]) // 2
    neutral_y = (Y_LIMITS[0] + Y_LIMITS[1]) // 2
```

**Lines 533-536**: Calculates center positions.

```python
    left_blink_open = BLINK_OPEN_LEFT
    right_blink_open = BLINK_OPEN_RIGHT

    current_servo_angles.update({
        LEFT_X: neutral_x,
        LEFT_Y: neutral_y,
        LEFT_BLINK: left_blink_open,
        RIGHT_X: neutral_x,
        RIGHT_Y: neutral_y,
        RIGHT_BLINK: right_blink_open
    })
```

**Lines 538-547**: Updates angle dictionary with center positions.

```python
    set_servo_angle(LEFT_X, DIR_LEFT_X, neutral_x)
    set_servo_angle(LEFT_Y, DIR_LEFT_Y, neutral_y)
    set_servo_angle(LEFT_BLINK, DIR_LEFT_BLINK, left_blink_open)

    set_servo_angle(RIGHT_X, DIR_RIGHT_X, neutral_x)
    set_servo_angle(RIGHT_Y, DIR_RIGHT_Y, neutral_y)
    set_servo_angle(RIGHT_BLINK, DIR_RIGHT_BLINK, right_blink_open)
```

**Lines 549-555**: Actually moves servos to center positions.

```python
def set_eyelids_closed():
    """Close both eyelids fully (sleep state)."""
    closed = BLINK_LIMITS[1]

    # 1. Drive eyelids to the closed angle
    set_servo_angle(LEFT_BLINK, DIR_LEFT_BLINK, closed)
    set_servo_angle(RIGHT_BLINK, DIR_RIGHT_BLINK, closed)
    current_servo_angles[LEFT_BLINK] = closed
    current_servo_angles[RIGHT_BLINK] = closed

    # 2. Give the servos time to actually move there
    time.sleep(0.3)  # tweak 0.2–0.4s if needed

    # 3. Then relax the servos by turning off PWM on those channels
    pca.channels[LEFT_BLINK].duty_cycle = 0
    pca.channels[RIGHT_BLINK].duty_cycle = 0
```

**Lines 558-574**:

-   Closes eyelids for sleep mode
-   Waits for movement to complete
-   Turns off PWM (relaxes servos, saves power, prevents jitter)

```python
def set_eyelids_open():
    """Open both eyelids to normal trim (awake state)."""
    left_open = BLINK_OPEN_LEFT
    right_open = BLINK_OPEN_RIGHT
    set_servo_angle(LEFT_BLINK, DIR_LEFT_BLINK, left_open)
    set_servo_angle(RIGHT_BLINK, DIR_RIGHT_BLINK, right_open)
    current_servo_angles[LEFT_BLINK] = left_open
    current_servo_angles[RIGHT_BLINK] = right_open
```

**Lines 576-584**: Opens eyelids to awake position.

```python
def set_offline_face():
    """
    Show a clear visual 'no internet' state:
    - Cross-eyed
    - Red mouth blink
    """
    global is_offline, is_thinking, is_speaking
    is_offline = True
    is_thinking = False
    is_speaking = False
```

**Lines 586-595**:

-   Sets offline state flags
-   Stops thinking/speaking states

```python
    # Cross-eye pose: left eye looks right, right eye looks left
    neutral_y = (Y_LIMITS[0] + Y_LIMITS[1]) // 2
    left_x_cross = X_LIMITS[1]   # rightmost
    right_x_cross = X_LIMITS[0]  # leftmost
```

**Lines 597-600**:

-   Calculates cross-eyed positions
-   Left eye looks right (max X), right eye looks left (min X)

```python
    targets = {
        LEFT_X: (DIR_LEFT_X, left_x_cross),
        LEFT_Y: (DIR_LEFT_Y, neutral_y),
        RIGHT_X: (DIR_RIGHT_X, right_x_cross),
        RIGHT_Y: (DIR_RIGHT_Y, neutral_y),
    }
    move_servos_together(targets, current_servo_angles)

    # Make sure eyelids are open so the pose is visible
    set_eyelids_open()

    # Red mouth blink a few times
    for _ in range(3):
        show_mouth(1.0, color=(255, 0, 0))
        time.sleep(0.25)
        clear_mouth()
        time.sleep(0.25)
```

**Lines 602-618**:

-   Moves eyes to cross-eyed position
-   Opens eyelids
-   Blinks red mouth 3 times as error indicator

---

### Section 11: Audio Recording and Transcription (Lines 621-777)

```python
def transcribe_audio(filename):
    """Use Whisper API to convert audio to text."""
    print("🧠 Transcribing...")

    try:
        with open(filename, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        # If we got here, internet is working again
        global is_offline
        is_offline = False
        return result.text.strip()
```

**Lines 625-638**:

-   Opens audio file
-   Sends to OpenAI Whisper API
-   If successful, clears offline flag
-   Returns transcribed text

```python
    except APIConnectionError:
        print("❌ No internet: cannot reach OpenAI for transcription. Check Wi-Fi.")
        set_offline_face()
        return ""
```

**Lines 639-642**:

-   Catches connection errors
-   Sets offline visual state
-   Returns empty string

```python
def is_meaningful_text(text: str) -> bool:
```

**Line 645**: Filters out noise and meaningless transcriptions.

```python
    """
    Heuristic filter to ignore background noise / nonsense.
    Returns False for very short, low-information, or non-speechy strings.
    Allows specific short commands like 'stop', 'exit', 'quit'.
    """
    if not text:
        return False

    t = text.strip().lower()
```

**Lines 646-654**:

-   Documentation
-   Early exit for empty text
-   Normalizes text (lowercase, trimmed)

```python
    # Always allow these short commands
    ALWAYS_ALLOW = {"stop", "exit", "quit"}
    if t in ALWAYS_ALLOW:
        return True
```

**Lines 656-659**: Allows exit commands even if short.

```python
    # Too short overall (e.g., "uh", "ok")
    if len(t) < 5:
        return False
```

**Lines 661-663**: Rejects very short text (< 5 characters).

```python
    # Very few alphabetic characters (mostly symbols / numbers)
    letters = sum(1 for c in t if c.isalpha())
    non_space = sum(1 for c in t if not c.isspace())
    if non_space > 0 and letters / non_space < 0.5:
        return False
```

**Lines 665-669**:

-   Counts letters vs non-space characters
-   Rejects if < 50% letters (too many symbols/numbers)

```python
    # Require at least 2 words with some vowels
    words = [w for w in re.split(r"\s+", t) if w]
    if len(words) < 2:
        return False

    if not any(ch in "aeiou" for ch in t):
        return False
```

**Lines 671-677**:

-   Requires at least 2 words
-   Requires at least one vowel

```python
    # Add any specific junk patterns Whisper often produces in your room:
    NOISE_PATTERNS = {"uh", "umm", "mm", "hmm"}
    if t in NOISE_PATTERNS:
        return False

    return True
```

**Lines 679-683**:

-   Filters common noise patterns
-   Returns True if passes all checks

```python
def record_audio(filename="input.wav", threshold=2400, silence_duration=0.6):
```

**Line 692**: Voice-activated audio recorder.

```python
    """
    Voice-activated audio recorder:
      - Starts when RMS > threshold
      - Stops when RMS < threshold for silence_duration seconds
      - Aborts immediately if the listen button is turned OFF
    """
    audio_interface = pyaudio.PyAudio()

    RATE = 44100
    CHUNK = 1024
```

**Lines 693-701**:

-   Documentation
-   Creates PyAudio instance
-   Sets sample rate (44.1 kHz) and chunk size (1024 samples)

```python
    input_index, _ = find_audio_devices()
    if input_index is None:
        print("❌ No microphone found.")
        return None
```

**Lines 703-706**:

-   Finds USB microphone
-   Returns None if not found

```python
    stream = audio_interface.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        input=True,
        input_device_index=input_index,
        frames_per_buffer=CHUNK
    )
```

**Lines 708-716**:

-   Opens audio input stream
-   16-bit integer format, mono (1 channel)
-   Uses found microphone device

```python
    print("🎤 Listening for speech...")

    frames = []
    recording_started = False
    silence_start = None
```

**Lines 718-722**:

-   Initializes recording state
-   `frames`: stores audio chunks
-   `recording_started`: True after speech detected
-   `silence_start`: timestamp when silence began

```python
    try:
        while True:
            update_listen_led_state()

            # Abort if button turned off
            if listen_button.value:
                print("🔕 Button turned off — cancelling recording.")
                break
```

**Lines 724-732**:

-   Main recording loop
-   Updates LED state
-   Exits if button released (button.value = True means not pressed)

```python
            data = stream.read(CHUNK, exception_on_overflow=False)
            rms = audioop.rms(data, 2)
```

**Lines 734-735**:

-   Reads audio chunk (1024 samples)
-   Calculates RMS (Root Mean Square) - measures volume

```python
            if not recording_started:
                # Wait for speech above noise floor
                if rms >= threshold:
                    print("🛑 Recording started!")
                    recording_started = True
                    frames.append(data)
                continue
```

**Lines 737-743**:

-   Before speech detected: waits for RMS > threshold
-   When detected, starts recording and saves first chunk

```python
            # Once recording has started:
            frames.append(data)

            # Detect silence
            if rms < threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= silence_duration:
                    print("🛑 Silence detected — stopping.")
                    break
            else:
                silence_start = None
```

**Lines 745-755**:

-   Always saves audio chunk
-   If volume drops below threshold:
    -   Starts silence timer (or checks if enough time passed)
    -   Stops after 0.6 seconds of silence
-   If volume rises again, resets silence timer

```python
    except KeyboardInterrupt:
        print("\n🛑 Recording interrupted.")
```

**Lines 757-759**: Handles Ctrl+C interruption.

```python
    print("🛑 Finished recording.")

    stream.stop_stream()
    stream.close()
    audio_interface.terminate()
```

**Lines 761-764**:

-   Closes audio stream and PyAudio instance

```python
    if not frames:
        print("⚠️ No audio captured.")
        return None
```

**Lines 766-768**: Returns None if no audio recorded.

```python
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio_interface.get_sample_size(pyaudio.paInt16))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
```

**Lines 770-775**:

-   Creates WAV file
-   Sets format (mono, 16-bit, 44.1 kHz)
-   Writes all audio chunks

```python
    return filename
```

**Line 776**: Returns filename of saved audio.

---

### Section 12: Text-to-Speech and Mouth Animation (Lines 779-878)

```python
def speak_text(text, color=(0, 0, 255)):
```

**Line 779**: Speaks text and animates mouth.

```python
    """Speak via TTS and animate mouth with amplitude levels."""
    global is_speaking, previous_audio_level

    is_speaking = True
```

**Lines 780-783**:

-   Sets speaking flag (prevents new recordings)
-   Resets audio level tracking

```python
    mp3_path = "speech_output.mp3"
    wav_path = "speech_output.wav"

    # Generate TTS
    try:
        with client.audio.speech.with_streaming_response.create(
            model=TTS_MODEL,
            voice=VOICE_NAME,
            input=text
        ) as response:
            response.stream_to_file(mp3_path)
        # If we got here, internet is working again
        global is_offline
        is_offline = False
```

**Lines 785-799**:

-   Defines file paths
-   Calls OpenAI TTS API with streaming response
-   Saves MP3 file
-   Clears offline flag if successful

```python
    except APIConnectionError:
        print("❌ No internet: cannot reach OpenAI for speech. Check Wi-Fi.")
        set_offline_face()
        is_speaking = False

        # Optional: a visual "error" blink using the mouth LEDs
        for _ in range(3):
            show_mouth(1.0, color=(255, 0, 0))
            time.sleep(0.25)
            clear_mouth()
            time.sleep(0.25)
        is_speaking = False
        return
```

**Lines 800-812**:

-   Handles connection errors
-   Shows offline face
-   Blinks red mouth 3 times
-   Returns early

```python
    # Convert to mono WAV at 48kHz
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-ac", "1", "-ar", "48000", wav_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
```

**Lines 814-819**:

-   Converts MP3 to WAV using ffmpeg
-   `-ac 1`: mono audio
-   `-ar 48000`: 48 kHz sample rate
-   Suppresses output

```python
    wave_file = wave.open(wav_path, 'rb')
    audio_interface = pyaudio.PyAudio()

    _, output_index = find_audio_devices()
    if output_index is None:
        print("❌ No speaker found.")
        return
```

**Lines 821-827**:

-   Opens WAV file for reading
-   Finds USB speaker
-   Returns if not found

```python
    output_stream = audio_interface.open(
        format=audio_interface.get_format_from_width(wave_file.getsampwidth()),
        channels=wave_file.getnchannels(),
        rate=48000,
        output=True,
        output_device_index=output_index,  # USB speaker index
    )
```

**Lines 829-835**:

-   Opens audio output stream
-   Matches WAV file format
-   Uses found speaker device

```python
    chunk_size = 512
    audio_playback_delay = 0.07  # lip-sync correction
```

**Lines 837-838**:

-   Smaller chunks for smoother animation
-   Delay compensates for processing time (lip sync)

```python
    data = wave_file.readframes(chunk_size)
    playback_start_time = time.time() + audio_playback_delay
```

**Lines 840-841**:

-   Reads first chunk
-   Calculates when playback should start (with delay)

```python
    while data:
        # Keep LED in sync with button even while speaking
        update_listen_led_state()

        rms = audioop.rms(data, 2) / 32768.0
        level = min(1.0, np.log10(1 + 55 * rms))
```

**Lines 843-848**:

-   Loops through all audio chunks
-   Updates LED state
-   Calculates RMS and normalizes (0-1 range)
-   Applies logarithmic scaling (makes quiet sounds more visible)

```python
        level = (
            MOUTH_SMOOTHING * previous_audio_level +
            (1 - MOUTH_SMOOTHING) * level
        )

        previous_audio_level = level

        show_mouth(level, color=color)
```

**Lines 850-857**:

-   Smooths audio level (blends with previous)
-   Updates previous level
-   Displays mouth animation with emotion color

```python
        while time.time() < playback_start_time:
            # Tight sync loop; could be relaxed if needed
            pass
```

**Lines 859-861**:

-   Waits until correct playback time
-   Ensures lip sync

```python
        output_stream.write(data)
        playback_start_time += chunk_size / wave_file.getframerate()
```

**Lines 863-864**:

-   Writes audio chunk to speaker
-   Calculates next chunk's playback time

```python
        data = wave_file.readframes(chunk_size)
```

**Line 866**: Reads next chunk.

```python
    clear_mouth()
    output_stream.stop_stream()
    output_stream.close()
    audio_interface.terminate()
    wave_file.close()

    os.remove(mp3_path)
    os.remove(wav_path)

    is_speaking = False
```

**Lines 868-877**:

-   Clears mouth LEDs
-   Closes audio streams and files
-   Deletes temporary files
-   Clears speaking flag

---

### Section 13: Main Loop (Lines 880-1080)

```python
def update_listen_led_state():
```

**Line 884**: Updates LED based on current state (non-blinking decisions).

```python
    """
    LED logic (non-blinking decisions):
    - OFF if switch off
    - BLINKING handled by led_blink_loop when busy
    - SOLID ON when armed & ready
    """
    global listen_led, is_armed, is_thinking, is_speaking

    if not is_armed:
        listen_led.value = False
    elif not (is_thinking or is_speaking):
        # Ready state
        listen_led.value = True
```

**Lines 885-897**:

-   Turns LED off if not armed
-   Turns LED on if armed and ready (not busy)
-   Blinking is handled by `led_blink_loop` thread

```python
def main():
    global is_running, is_thinking, last_blink_timestamp, is_armed

    center_eyes()
    clear_mouth()
```

**Lines 900-905**:

-   Initializes global variables
-   Centers eyes and clears mouth on startup

```python
    print("🤖 Animatronic Chatbot Ready.")

    # If we're in an interactive terminal, ask for ENTER.
    # If running under systemd/cron (no TTY), skip the prompt.
    if sys.stdin.isatty():
        input("Press ENTER to begin...")
    else:
        # Optional: small delay so you can see logs if run manually as a service
        time.sleep(1)
```

**Lines 907-914**:

-   Prints ready message
-   If running in terminal, waits for Enter key
-   If running as service (no TTY), just waits 1 second

```python
    # Start background threads
    eye_thread = threading.Thread(target=eyes_idle_loop)
    eye_thread.start()

    led_thread = threading.Thread(target=led_blink_loop)
    led_thread.start()

    idle_thread = threading.Thread(target=idle_speech_loop)
    idle_thread.start()
```

**Lines 916-924**:

-   Starts three background threads:
    1. Eye movement loop
    2. LED blink loop
    3. Idle speech loop
-   These run continuously in parallel

```python
    # ▶️ Startup announcement
    speak_text("I'm ready. Press the button and ask me a question.", color=(0, 255, 0))
```

**Lines 926-927**:

-   Speaks startup message with green color

```python
    # Initialize armed state based on current button, but DO NOT move lids yet
    button_on = not listen_button.value
    is_armed = button_on
    last_armed = button_on
```

**Lines 929-932**:

-   Reads initial button state
-   `not listen_button.value` because button is active-low (pressed = False)
-   Tracks previous state to detect changes

```python
    try:
        while True:
            # Update is_armed based on button
            button_on = not listen_button.value
            is_armed = button_on
```

**Lines 934-938**:

-   Main loop
-   Continuously reads button state

```python
            # Only move eyelids when the state changes AFTER startup
            if button_on != last_armed:
                if button_on:
                    set_eyelids_open()    # waking up
                else:
                    set_eyelids_closed()  # going to sleep
                last_armed = button_on
```

**Lines 940-947**:

-   Detects button state change
-   Opens eyelids when button pressed (wake)
-   Closes eyelids when button released (sleep)

```python
            # Update LED based on current state
            update_listen_led_state()

            # If switch is OFF: don't listen, just idle/sleep
            if not button_on:
                is_thinking = False
                time.sleep(0.05)
                continue
```

**Lines 949-955**:

-   Updates LED based on current state
-   If button off, clears thinking flag and skips listening
-   Short sleep (0.05s) to prevent CPU spinning in tight loop

```python
            # Switch is ON: listen once
            print("🎤 Listening for speech...")
            audio_path = record_audio()
```

**Lines 957-959**:

-   Button is ON, so system is ready to listen
-   Calls `record_audio()` which waits for voice activation
-   Returns path to recorded WAV file, or `None` if cancelled/no audio

```python
            # If recording was cancelled (button turned off or no audio), skip this turn
            if audio_path is None:
                is_thinking = False
                continue
```

**Lines 961-964**:

-   Checks if recording was successful
-   If `None`, user cancelled or no audio captured
-   Clears thinking flag and loops back to check button again

```python
            is_thinking = True
            user_text = transcribe_audio(audio_path)

            print(f"🧑 You said: {user_text}")

            os.remove(audio_path)
```

**Lines 966-971**:

-   Sets `is_thinking = True` (triggers thinking eye movements)
-   Sends audio file to OpenAI Whisper API for transcription
-   Prints what user said
-   Deletes temporary audio file to save disk space

```python
            # 1️⃣ Completely empty / whitespace → ignore
            if not user_text or not user_text.strip():
                print("⚠️ Nothing clear was transcribed; not sending to OpenAI.")
                is_thinking = False
                time.sleep(0.5)   # small pause so it doesn't spin too fast
                continue
```

**Lines 973-978**:

-   First validation: checks if transcription is empty
-   If empty/whitespace, skips OpenAI call (saves API costs)
-   Clears thinking flag and waits 0.5s before next attempt

```python
            norm = user_text.lower().strip()

            # 2️⃣ Exit commands (must work even if short)
            if norm in ["quit", "exit", "stop"]:
                is_running = False
                pca.deinit()
                clear_mouth()
                print("👋 Goodbye.")
                break
```

**Lines 980-988**:

-   Normalizes text to lowercase for comparison
-   Checks for exit commands (quit, exit, stop)
-   If found:
    -   Sets `is_running = False` (stops all background threads)
    -   Deinitializes PCA9685 (turns off servos)
    -   Clears mouth LEDs
    -   Prints goodbye and breaks out of main loop

```python
            # 3️⃣ Easter eggs (also allowed even if short-ish)
            if "wink for me" in norm or norm.startswith("wink") or "can you wink" in norm:
                is_thinking = False
                print("✨ Easter Egg: wink")
                wink()
                continue

            if "blink twice" in norm and "understand" in norm:
                is_thinking = False
                print("✨ Easter Egg: blink twice")
                blink_twice()
                continue
```

**Lines 990-1001**:

-   Special commands that trigger physical actions
-   Wink command: detects phrases like "wink for me", "wink", "can you wink"
-   Double blink: detects "blink twice if you understand"
-   Executes the action and continues loop (skips AI conversation)

```python
            # 4️⃣ Noise filter – ignore junk / room noise
            if not is_meaningful_text(user_text):
                print("⚠️ Transcription looks like noise; ignoring.")
                is_thinking = False
                time.sleep(0.5)
                continue
```

**Lines 1003-1008**:

-   Calls `is_meaningful_text()` to filter out background noise
-   Checks for minimum length, word count, vowel presence
-   If fails filter, ignores the transcription and continues

```python
            # ----------------------------------------------
            # Normal conversation
            # ----------------------------------------------
            print("🤔 Thinking...")

            try:
                response = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": (
                            "You are a calm, expressive AI. "
                            "Respond concisely in 1 sentence unless necessary. "
                            "Do NOT start with greetings like 'Hello', 'Hi', or 'How can I help you today?'. "
                            "Just answer the user's request directly. "
                            "Also output emotion as one of: happy, sad, neutral, angry, surprised. "
                            "Format: <text> [emotion: <label>]"
                        )},
                        {"role": "user", "content": user_text},
                    ]
                )
                global is_offline
                is_offline = False

            except APIConnectionError:
                print("❌ No internet: cannot reach OpenAI for chat completion. Check Wi-Fi.")
                # Optional visual feedback
                set_offline_face()
                for _ in range(3):
                    show_mouth(1.0, color=(255, 0, 0))
                    time.sleep(0.25)
                    clear_mouth()
                    time.sleep(0.25)
                is_thinking = False
                continue  # skip this turn and go back to waiting for the next question
```

**Lines 1010-1043**:

-   **Lines 1013**: Prints "Thinking..." message
-   **Lines 1015-1029**: Calls OpenAI GPT-4 API
    -   Uses `CHAT_MODEL` ("gpt-4.1-mini")
    -   System message instructs AI to:
        -   Be calm and expressive
        -   Respond concisely (1 sentence)
        -   Skip greetings
        -   Include emotion tag in format: `[emotion: happy]`
    -   User message contains transcribed text
-   **Lines 1030-1031**: If successful, clears offline flag
-   **Lines 1033-1043**: Error handling
    -   Catches `APIConnectionError` (no internet)
    -   Sets offline face (cross-eyed pose)
    -   Blinks red mouth 3 times
    -   Clears thinking flag and continues loop

```python
            # ----------------------------------------------
            # Handle model response + emotion
            # ----------------------------------------------
            full_reply = response.choices[0].message.content.strip()

            # Extract emotion
            match = re.search(r"\[emotion:\s*(\w+)\]", full_reply, re.IGNORECASE)
            emotion = match.group(1).lower() if match else "neutral"

            # Strip label before TTS
            reply_text = re.sub(r"\[emotion:.*\]", "", full_reply).strip()
```

**Lines 1045-1055**:

-   **Line 1048**: Gets AI's response text
-   **Lines 1051-1052**: Uses regex to find emotion tag like `[emotion: happy]`
    -   Extracts emotion word (happy, sad, neutral, angry, surprised)
    -   Defaults to "neutral" if not found
-   **Line 1055**: Removes emotion tag from text (so TTS doesn't say "[emotion: happy]")

```python
            EMOTION_COLORS = {
                "happy": (0, 255, 255),      # yellow-ish
                "sad": (255, 0, 0),          # blue
                "angry": (0, 255, 0),        # red
                "surprised": (255, 255, 0),  # purple
                "neutral": (0, 255, 0),      # default green
            }

            color = EMOTION_COLORS.get(emotion, (0, 255, 0))

            is_thinking = False

            print(f"🤖 {reply_text}  [{emotion}]")
            speak_text(reply_text, color=color)
```

**Lines 1057-1070**:

-   **Lines 1057-1063**: Maps emotions to RGB colors for mouth LEDs
    -   Note: Color values appear to be in BRG format based on Neopixel config
    -   happy = yellow, sad = blue, angry = red, surprised = purple, neutral = green
-   **Line 1065**: Gets color for detected emotion, defaults to green
-   **Line 1067**: Clears thinking flag (stops thinking eye movements)
-   **Line 1069**: Prints bot's response with emotion
-   **Line 1070**: Calls `speak_text()` which:
    -   Generates TTS audio
    -   Plays audio through USB speaker
    -   Animates mouth LEDs with emotion color

```python
    except KeyboardInterrupt:
        is_running = False
        pca.deinit()
        clear_mouth()
        print("\n👋 Program stopped.")
```

**Lines 1072-1076**:

-   Handles Ctrl+C keyboard interrupt
-   Sets `is_running = False` (stops background threads)
-   Deinitializes PCA9685
-   Clears mouth LEDs
-   Prints goodbye message

```python
if __name__ == "__main__":
    main()
```

**Lines 1079-1080**:

-   Standard Python idiom: only runs `main()` if script is executed directly
-   Prevents execution if file is imported as a module
-   Entry point of the entire program

---

## 🔄 Program Flow Summary

### Startup Sequence:

1. **Script execution** (`start_chatbot.sh` or `python AIChatbot.py`)
2. **Imports load** - All libraries and modules initialize
3. **Hardware initialization** - I2C, PCA9685, GPIO pins, Neopixel
4. **OpenAI client** - Connects with API key from `.env`
5. **Eyes center** - Servos move to neutral position
6. **Background threads start**:
    - `eyes_idle_loop()` - Eye movements
    - `led_blink_loop()` - Status LED
    - `idle_speech_loop()` - Idle phrases
7. **Startup message** - "I'm ready. Press the button..."
8. **Main loop begins**

### Main Loop Cycle:

1. **Check button state** - Is it pressed?
2. **If OFF**: Close eyelids, sleep, loop
3. **If ON**:
    - Open eyelids
    - Update LED (solid = ready, blink = busy)
    - Record audio (voice-activated)
    - Transcribe with Whisper
    - Validate transcription
    - Check for exit/easter egg commands
    - Send to GPT-4
    - Extract emotion
    - Generate TTS
    - Speak with animated mouth
    - Loop back to step 1

### Background Threads (Running Simultaneously):

**`eyes_idle_loop()`**:

-   Continuously moves eyes based on state (idle/thinking/speaking)
-   Triggers automatic blinks
-   Stops when `is_running = False`

**`led_blink_loop()`**:

-   Updates status LED based on armed/thinking/speaking states
-   Blinks when busy, solid when ready
-   Stops when `is_running = False`

**`idle_speech_loop()`**:

-   Monitors time since last interaction
-   After 90 seconds, speaks random idle phrase
-   Stops when `is_running = False`

---

## 🎯 Key Concepts

### State Variables:

-   `is_running`: Global flag to stop all threads
-   `is_armed`: Button is ON (system active)
-   `is_thinking`: Processing user input
-   `is_speaking`: Currently playing TTS audio
-   `is_offline`: Internet connection failed

### Servo Control:

-   Uses PCA9685 PWM driver for 6 servos
-   Smooth interpolation between positions
-   Direction multipliers handle inverted servos
-   Limits prevent over-travel

### Audio Pipeline:

1. **Record**: PyAudio captures from USB mic
2. **Save**: WAV file written to disk
3. **Transcribe**: OpenAI Whisper API
4. **Process**: GPT-4 generates response
5. **Synthesize**: OpenAI TTS creates MP3
6. **Convert**: FFmpeg converts to WAV
7. **Play**: PyAudio streams to USB speaker
8. **Animate**: Mouth LEDs sync with audio amplitude

### Emotion System:

-   GPT-4 instructed to include `[emotion: <label>]` in responses
-   Regex extracts emotion tag
-   Color mapping drives Neopixel mouth animation
-   Provides visual feedback matching AI's emotional state

---

## 📚 Additional Notes

### Error Handling:

-   **No internet**: Cross-eyed pose, red mouth blinks
-   **No audio devices**: Prints error, continues
-   **API errors**: Catches exceptions, visual feedback
-   **Keyboard interrupt**: Graceful shutdown

### Performance Optimizations:

-   Background threads prevent blocking
-   Audio files deleted after use
-   Short sleep delays prevent CPU spinning
-   Smooth servo interpolation reduces jitter

### Customization Points:

-   `USE_PI5`: Platform selection
-   `X_LIMITS`, `Y_LIMITS`: Eye movement range
-   `BLINK_INTERVAL`: Blink frequency
-   `IDLE_INTERVAL`: Time before idle speech
-   `MOUTH_SMOOTHING`: Animation smoothness
-   `threshold`: Voice activation sensitivity
-   `silence_duration`: Recording stop delay

---

**End of Code Explanation**
