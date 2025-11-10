#!/usr/bin/env python3
"""
Check the audio file properties
"""
import json
import base64
import struct
import wave
import io

# Load audio sample
with open('asr/audio_samples.json', 'r') as f:
    data = json.load(f)
    audio_base64 = data['audio_samples'][0]

# Decode from base64
audio_bytes = base64.b64decode(audio_base64)

print(f"=== Audio File Info ===")
print(f"Total bytes: {len(audio_bytes)}")
print(f"First 20 bytes (hex): {audio_bytes[:20].hex()}")
print(f"First 4 bytes (ASCII): {audio_bytes[:4].decode('ascii', errors='ignore')}")

# Try to parse WAV header
try:
    wav_file = wave.open(io.BytesIO(audio_bytes), 'rb')
    print(f"\n=== WAV Properties ===")
    print(f"Channels: {wav_file.getnchannels()}")
    print(f"Sample Width: {wav_file.getsampwidth()} bytes")
    print(f"Frame Rate (Sample Rate): {wav_file.getframerate()} Hz")
    print(f"Number of Frames: {wav_file.getnframes()}")
    print(f"Duration: {wav_file.getnframes() / wav_file.getframerate():.2f} seconds")
    print(f"Compression Type: {wav_file.getcomptype()}")

    # Read some audio data to check if it's silent
    frames = wav_file.readframes(1000)
    if len(frames) > 0:
        # Convert bytes to integers (assuming 16-bit audio)
        samples = struct.unpack(f'{len(frames)//2}h', frames)
        max_amplitude = max(abs(s) for s in samples)
        avg_amplitude = sum(abs(s) for s in samples) / len(samples)
        print(f"\n=== Audio Signal Check ===")
        print(f"Max amplitude: {max_amplitude} (out of 32767)")
        print(f"Average amplitude: {avg_amplitude:.2f}")
        if max_amplitude < 100:
            print("⚠️  WARNING: Audio appears to be very quiet or silent!")
        else:
            print("✓ Audio has detectable signal")

    wav_file.close()
except Exception as e:
    print(f"\nError reading WAV file: {e}")
