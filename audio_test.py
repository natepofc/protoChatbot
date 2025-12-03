#!/usr/bin/env python3
"""
Audio Test Script
Tests microphone recording and playback on Mac
"""

import pyaudio
import wave
import time
import sys
import audioop

# Audio settings
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 3  # Record for 3 seconds
OUTPUT_FILENAME = "test_recording.wav"


def find_audio_devices():
    """Find available audio input and output devices."""
    p = pyaudio.PyAudio()
    input_index = None
    output_index = None
    default_input = None
    default_output = None

    # Get default devices
    try:
        default_input = p.get_default_input_device_info().get("index")
        default_output = p.get_default_output_device_info().get("index")
    except:
        pass

    print("\n📋 Available Audio Devices:")
    print("=" * 60)
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info.get("name", "Unknown")
        max_input = info.get("maxInputChannels", 0)
        max_output = info.get("maxOutputChannels", 0)
        
        device_type = []
        if max_input > 0:
            device_type.append("INPUT")
        if max_output > 0:
            device_type.append("OUTPUT")
        
        device_str = " / ".join(device_type) if device_type else "N/A"
        
        # Mark default devices
        marker = ""
        if i == default_input:
            marker += " [DEFAULT INPUT]"
        if i == default_output:
            marker += " [DEFAULT OUTPUT]"
        
        print(f"  [{i}] {name} - {device_str}{marker}")
        
        # Auto-select first input device
        if input_index is None and max_input > 0:
            input_index = i
        
        # Auto-select first output device
        if output_index is None and max_output > 0:
            output_index = i

    # Fall back to defaults if no devices found
    if input_index is None and default_input is not None:
        input_index = default_input
    if output_index is None and default_output is not None:
        output_index = default_output

    p.terminate()
    return input_index, output_index


def test_recording():
    """Test microphone recording."""
    print("\n🎤 Testing Microphone Recording...")
    print("=" * 60)
    
    audio_interface = pyaudio.PyAudio()
    
    # Find audio devices
    input_index, output_index = find_audio_devices()
    
    if input_index is None:
        print("❌ No input device (microphone) found!")
        audio_interface.terminate()
        return None
    
    # Show which device is being used
    device_info = audio_interface.get_device_info_by_index(input_index)
    print(f"\n✅ Using input device: {device_info.get('name', 'Unknown')}")
    print(f"   Sample Rate: {RATE} Hz")
    print(f"   Channels: 1 (mono)")
    
    # Open audio stream for recording
    try:
        stream = audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            input_device_index=input_index,
            frames_per_buffer=CHUNK
        )
    except Exception as e:
        print(f"❌ Error opening audio stream: {e}")
        audio_interface.terminate()
        return None
    
    print(f"\n🔴 Recording for {RECORD_SECONDS} seconds...")
    print("   Speak now!")
    print("   (Monitoring audio levels - you should see RMS values when speaking)\n")
    
    frames = []
    max_rms = 0
    min_rms = float('inf')
    samples_with_audio = 0
    
    # Record audio
    try:
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Calculate RMS to check if audio is being captured
            rms = audioop.rms(data, 2)
            if rms > max_rms:
                max_rms = rms
            if rms < min_rms:
                min_rms = rms
            if rms > 500:  # Threshold for "has audio"
                samples_with_audio += 1
            
            # Show progress with audio level
            if i % 10 == 0:
                progress = int((i / (RATE / CHUNK * RECORD_SECONDS)) * 100)
                print(f"   Recording... {progress}% | RMS: {rms:6d} | Max: {max_rms:6d}", end='\r')
        
        print(f"   Recording... 100% - Complete!                    ")
        print(f"\n   Audio Statistics:")
        print(f"   - Min RMS: {min_rms}")
        print(f"   - Max RMS: {max_rms}")
        print(f"   - Samples with audio (>500): {samples_with_audio}/{int(RATE / CHUNK * RECORD_SECONDS)}")
        
        if max_rms < 500:
            print(f"\n   ⚠️  WARNING: Very low audio levels detected!")
            print(f"   This might indicate:")
            print(f"   1. Microphone permissions not granted (check System Preferences)")
            print(f"   2. Microphone is muted or volume is very low")
            print(f"   3. No sound was captured during recording")
        elif samples_with_audio < 10:
            print(f"\n   ⚠️  WARNING: Very little audio detected!")
            print(f"   Only {samples_with_audio} samples had significant audio.")
        else:
            print(f"\n   ✅ Good audio levels detected!")
        
    except Exception as e:
        print(f"\n❌ Error during recording: {e}")
        stream.stop_stream()
        stream.close()
        audio_interface.terminate()
        return None
    
    # Stop and close stream
    stream.stop_stream()
    stream.close()
    audio_interface.terminate()
    
    if not frames:
        print("❌ No audio data captured!")
        return None
    
    # Save to file
    print(f"\n💾 Saving recording to {OUTPUT_FILENAME}...")
    try:
        with wave.open(OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(audio_interface.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))
        print(f"✅ Recording saved successfully!")
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return None
    
    return OUTPUT_FILENAME


def test_playback(filename):
    """Test audio playback."""
    print("\n🔊 Testing Audio Playback...")
    print("=" * 60)
    
    if not filename:
        print("❌ No audio file to play!")
        return False
    
    audio_interface = pyaudio.PyAudio()
    
    # Find output device
    _, output_index = find_audio_devices()
    
    if output_index is None:
        print("❌ No output device (speaker) found!")
        audio_interface.terminate()
        return False
    
    # Show which device is being used
    device_info = audio_interface.get_device_info_by_index(output_index)
    print(f"\n✅ Using output device: {device_info.get('name', 'Unknown')}")
    
    # Open WAV file
    try:
        wave_file = wave.open(filename, 'rb')
    except Exception as e:
        print(f"❌ Error opening audio file: {e}")
        audio_interface.terminate()
        return False
    
    # Open audio stream for playback
    try:
        output_stream = audio_interface.open(
            format=audio_interface.get_format_from_width(wave_file.getsampwidth()),
            channels=wave_file.getnchannels(),
            rate=wave_file.getframerate(),
            output=True,
            output_device_index=output_index,
        )
    except Exception as e:
        print(f"❌ Error opening output stream: {e}")
        wave_file.close()
        audio_interface.terminate()
        return False
    
    print(f"\n▶️  Playing back recording...")
    
    # Play audio
    chunk_size = 1024
    data = wave_file.readframes(chunk_size)
    
    try:
        while data:
            output_stream.write(data)
            data = wave_file.readframes(chunk_size)
    except Exception as e:
        print(f"❌ Error during playback: {e}")
        output_stream.stop_stream()
        output_stream.close()
        wave_file.close()
        audio_interface.terminate()
        return False
    
    # Clean up
    output_stream.stop_stream()
    output_stream.close()
    audio_interface.terminate()
    wave_file.close()
    
    print("✅ Playback complete!")
    return True


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("🎙️  MAC AUDIO TEST SCRIPT")
    print("=" * 60)
    
    # Test recording
    recorded_file = test_recording()
    
    if recorded_file:
        # Wait a moment
        time.sleep(0.5)
        
        # Test playback
        test_playback(recorded_file)
        
        print("\n" + "=" * 60)
        print("✅ Test Complete!")
        print(f"📁 Test recording saved as: {recorded_file}")
        print("=" * 60)
    else:
        print("\n❌ Recording test failed. Please check your microphone settings.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

