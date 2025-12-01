# Animatronic AI Chatbot for Raspberry Pi 5

An interactive animatronic chatbot that combines OpenAI's GPT-4 and TTS APIs with physical servo-controlled eyes, Neopixel mouth LEDs, and voice interaction. The robot can have natural conversations, express emotions through colored mouth animations, and respond to voice commands.

## 🎯 Overview

This project creates a fully interactive animatronic robot head that:

-   **Listens** to your voice through a USB microphone
-   **Thinks** with OpenAI's GPT-4 model
-   **Speaks** using OpenAI's text-to-speech (TTS) API
-   **Moves** its eyes using 6 servo motors (X/Y position and blinking for each eye)
-   **Animates** its mouth with 8 Neopixel LEDs that respond to speech amplitude
-   **Expresses emotions** through color-coded mouth animations
-   **Sleeps/Wakes** based on a physical button toggle

## 🏗️ Hardware Requirements

### Required Components

-   **Raspberry Pi 5** (or Pi 4 with code modification)
-   **PCA9685 PWM Servo Driver** (16-channel I2C)
-   **6x Servo Motors**:
    -   2x for left eye X/Y movement
    -   2x for right eye X/Y movement
    -   2x for left/right eyelid blinking
-   **8x Neopixel LEDs** (WS2812B or compatible) for mouth animation
-   **USB Microphone** (for voice input)
-   **USB Speaker** (for audio output)
-   **Push Button** (connected to GPIO22 with pull-up resistor)
-   **LED** (connected to GPIO23) for status indication
-   **Power Supply** (adequate for servos and Raspberry Pi)

### GPIO Pin Connections

-   **GPIO22 (Physical Pin 15)**: Listen button (pull-up, pressed = LOW)
-   **GPIO23 (Physical Pin 16)**: Status LED
-   **GPIO13 (Physical Pin 33)**: Neopixel data line
-   **I2C (SDA/SCL)**: PCA9685 servo driver

## 📦 Software Dependencies

### Python Packages

-   `openai` - OpenAI API client
-   `python-dotenv` - Environment variable management
-   `pyaudio` - Audio I/O
-   `numpy` - Numerical operations
-   `adafruit-circuitpython-pca9685` - PCA9685 servo driver
-   `adafruit-circuitpython-neopixel` - Neopixel control (Pi 4)
-   `adafruit-raspberry-pi5-neopixel` - Neopixel control (Pi 5)
-   `adafruit-blinka` - CircuitPython compatibility layer
-   `rpi-lgpio` - GPIO access for Pi 5

### System Requirements

-   **Raspberry Pi OS** (or compatible Linux distribution)
-   **ffmpeg** - Audio format conversion
-   **Python 3.11+**

## 🔧 Setup Instructions

### 1. Clone and Navigate

```bash
cd /path/to/protoChatbot
```

### 2. Create Virtual Environment

```bash
python3 -m venv cb-env
source cb-env/bin/activate
```

### 3. Install Dependencies

```bash
pip install openai python-dotenv pyaudio numpy
pip install adafruit-circuitpython-pca9685
pip install adafruit-circuitpython-neopixel  # For Pi 4
pip install adafruit-raspberry-pi5-neopixel  # For Pi 5
pip install adafruit-blinka
pip install rpi-lgpio  # For Pi 5 GPIO
```

### 4. Configure OpenAI API Key

Create a `.env` file in the project root:

```bash
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### 5. Hardware Configuration

-   Connect servos to PCA9685 channels 0-5 as defined in the code
-   Connect Neopixel strip to GPIO13
-   Connect button to GPIO22 (with pull-up resistor)
-   Connect status LED to GPIO23
-   Ensure USB microphone and speaker are connected

### 6. Adjust Platform Setting

In `AIChatbot.py`, line 29:

```python
USE_PI5 = True  # Set to False for Raspberry Pi 4
```

## 🚀 Usage

### Running the Main Chatbot

```bash
source cb-env/bin/activate
python AIChatbot.py
```

Or use the startup script:

```bash
./start_chatbot.sh
```

### Testing Eye Movement Only

To test servo movements independently:

```bash
python EyeMovement.py
```

## 🎮 How It Works

### Main Loop Flow

1. **Initialization**: Eyes center, mouth clears, servos initialize
2. **Button Check**: System checks if listen button is pressed
3. **Sleep Mode**: If button OFF, eyelids close, system idles
4. **Wake Mode**: If button ON, eyelids open, LED indicates ready state
5. **Voice Recording**: When armed, records audio until silence detected
6. **Transcription**: Audio sent to OpenAI Whisper API
7. **Chat Processing**: User text sent to GPT-4 with emotion extraction
8. **Speech Synthesis**: Response converted to speech via TTS
9. **Mouth Animation**: Neopixels animate based on audio amplitude
10. **Eye Movement**: Eyes move randomly during idle/thinking/speaking modes

### Eye Movement Modes

-   **Idle**: Random eye movements with natural blinking (every 7-12 seconds)
-   **Thinking**: Smaller, faster eye movements with frequent blinks
-   **Speaking**: Subtle eye movements synchronized with speech
-   **Offline**: Cross-eyed pose when internet connection fails

### Mouth Animation

-   **Amplitude-based**: LED brightness/quantity reflects speech volume
-   **Emotion colors**:
    -   🟢 Green: Neutral
    -   🟡 Yellow: Happy
    -   🔴 Red: Sad/Angry
    -   🟣 Purple: Surprised
-   **Symmetric display**: LEDs light from center outward

### Status LED Behavior

-   **OFF**: System not armed (button off)
-   **Solid ON**: Ready to listen
-   **Blinking**: Busy (thinking or speaking)

### Idle Speech

After 90 seconds of silence, the robot will randomly say one of:

-   "Ready when you are."
-   "Anything I can help with?"
-   "I'm here whenever you need me."
-   "Just say the word."
-   "How can I help?"

## 🎯 Features

### Voice Interaction

-   **Voice-activated recording**: Starts when speech detected above threshold
-   **Silence detection**: Stops recording after 0.6 seconds of silence
-   **Noise filtering**: Filters out background noise and meaningless transcriptions
-   **Button cancellation**: Can cancel recording by releasing button

### AI Capabilities

-   **GPT-4.1-mini**: Conversational AI model
-   **Emotion detection**: Extracts emotion from responses (happy, sad, neutral, angry, surprised)
-   **Concise responses**: Configured for 1-sentence answers unless needed
-   **No greeting spam**: Skips unnecessary greetings

### Physical Expressions

-   **Natural blinking**: Staggered eyelid motion for realism
-   **Random eye movement**: Idle eyes wander naturally
-   **Wink command**: Say "wink for me" for a single-eye wink
-   **Double blink**: Say "blink twice if you understand" for double blink
-   **Sleep mode**: Eyelids close when button is off, servos relax

### Error Handling

-   **Offline detection**: Detects internet connectivity issues
-   **Visual error feedback**: Red mouth blinks when offline
-   **Graceful degradation**: Continues operating when possible

## ⚙️ Configuration

### Key Settings in `AIChatbot.py`

#### Servo Configuration

```python
X_LIMITS = (70, 110)      # Eye X-axis movement range
Y_LIMITS = (70, 110)      # Eye Y-axis movement range
BLINK_LIMITS = (0, 40)    # Eyelid movement range
```

#### Audio Settings

```python
threshold = 2400          # Voice activation threshold
silence_duration = 0.6    # Seconds of silence to stop recording
```

#### Timing

```python
BLINK_INTERVAL = (7, 12)  # Seconds between automatic blinks
IDLE_INTERVAL = 90        # Seconds before idle speech triggers
```

#### Mouth Animation

```python
MOUTH_SMOOTHING = 0.6     # Smoothing factor (0=jumpy, 1=smooth)
NUM_PIXELS = 8            # Number of Neopixel LEDs
```

## 🐛 Troubleshooting

### Audio Issues

-   **No microphone found**: Check USB connection, verify with `arecord -l`
-   **No speaker found**: Check USB connection, verify with `aplay -l`
-   **Low volume**: Adjust system volume with `alsamixer`

### Servo Issues

-   **Jittery movement**: Check power supply, ensure adequate current
-   **Wrong positions**: Adjust `X_LIMITS`, `Y_LIMITS`, or direction multipliers
-   **Eyelids not closing**: Check `BLINK_LIMITS` and `BLINK_OPEN_LEFT/RIGHT` values

### Neopixel Issues

-   **Wrong colors**: Adjust `byteorder` parameter (line 167) or `pixel_order` (line 179)
-   **Not lighting**: Check GPIO13 connection and power supply

### API Issues

-   **Connection errors**: Verify `.env` file has correct `OPENAI_API_KEY`
-   **Rate limits**: Check OpenAI API usage and billing
-   **Offline mode**: Check internet connection, Wi-Fi status

## 📝 Code Structure

### `AIChatbot.py` (Main Application)

-   **Lines 1-45**: Imports and configuration
-   **Lines 47-78**: Audio device detection
-   **Lines 80-209**: Servo and Neopixel setup
-   **Lines 211-228**: Button and LED GPIO setup
-   **Lines 230-473**: Servo control and eye movement functions
-   **Lines 475-530**: LED and idle speech loops
-   **Lines 532-619**: Eye positioning and offline state functions
-   **Lines 621-777**: Audio recording and transcription
-   **Lines 779-878**: Text-to-speech and mouth animation
-   **Lines 880-1080**: Main loop and conversation handling

### `EyeMovement.py` (Test Utility)

-   Standalone script for testing servo movements
-   Useful for calibration and debugging eye mechanics

## 🔒 Safety Notes

-   **Servo Power**: Ensure servos have adequate power supply separate from Pi
-   **Neopixel Power**: Neopixels may require external power for full brightness
-   **GPIO Protection**: Use appropriate resistors for button/LED connections
-   **Shutdown**: Always properly shut down to avoid servo damage

## 📄 License

MIT Open Source License

## 👤 Dave Robertson & Nate Patel

[Add author information here]

## 🙏 Acknowledgments

-   OpenAI for GPT-4 and TTS APIs
-   Adafruit for CircuitPython libraries
-   Raspberry Pi Foundation for hardware platform
