from pynput import mouse
import numpy as np
import pyaudio
import threading
import time

# Generate a "ding" sound in memory with a custom envelope
def generate_ding(frequency=200.0, duration=0.2, volume=0.05, sample_rate=44100):
    """
    Generate a ding sound with a custom volume envelope and return it as a numpy array.
    - frequency: Pitch of the ding in Hz (default: 880Hz).
    - duration: Duration of the ding in seconds (default: 1.3s).
    - volume: Volume of the ding (0.0 to 1.0, default: 0.5).
    - sample_rate: Sample rate in Hz (default: 44100Hz).
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)  # Time axis

    # Sine wave generator
    waveform = np.sin(2 * np.pi * frequency * t) * volume * 32767

    # Calculate the envelope length
    total_length = len(waveform)

    # Custom envelope: First 1.5s or 10% of the time, whichever is shorter
    max_attack_samples = int(1.5 * sample_rate)  # 1.5 seconds in samples
    ten_percent_samples = int(0.1 * total_length)  # 10% of the waveform length
    attack_duration = min(max_attack_samples, ten_percent_samples)  # Shorter of the two

    decay_duration = total_length - attack_duration  # Remaining time

    envelope = np.concatenate([
        np.linspace(1, 0.1, attack_duration),  # Rapid decrease to 10% volume
        np.linspace(0.1, 0, decay_duration)   # Gradual fade to 0
    ])

    # Apply envelope and convert to 16-bit PCM
    waveform = (waveform * envelope).astype(np.int16)
    return waveform

# Audio playback class
class AudioPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.ding_duration = 0.2
        self.base_frequency = 400.0

        # Create a "revolver" of 3 audio streams
        self.streams = [self._create_stream() for _ in range(3)]
        self.active_stream_index = 0
        self.last_ding_time = 0
        self.current_frequency = self.base_frequency
        self.lock = threading.Lock()

    def _create_stream(self):
        """
        Create and return a new PyAudio stream.
        """
        return self.p.open(format=pyaudio.paInt16,
                           channels=1,
                           rate=44100,
                           output=True)

    def _reset_stream(self, stream_index):
        """
        Reset a specific stream in the revolver if it encounters an error.
        """
        try:
            self.streams[stream_index].stop_stream()
            self.streams[stream_index].close()
        except Exception as e:
            print(f"Error stopping/closing stream {stream_index}: {e}")

        # Recreate the stream
        self.streams[stream_index] = self._create_stream()

    def _play_sound(self, stream_index, ding_sound):
        """
        Play the given sound on the specified stream.
        This is executed in a separate thread to avoid blocking the main thread.
        """
        stream = self.streams[stream_index]
        try:
            stream.start_stream()
            stream.write(ding_sound.tobytes())
            stream.stop_stream()
        except Exception as e:
            print(f"Error with stream {stream_index}: {e}")
            self._reset_stream(stream_index)

    def play_ding(self):
        with self.lock:
            current_time = time.time()
            time_since_last_ding = current_time - self.last_ding_time

            # Check if the new ding is within the duration of the previous ding
            if time_since_last_ding < self.ding_duration:
                # Increase the frequency for the new ding
                self.current_frequency += 50.0
            else:
                # Reset the frequency to the baseline
                self.current_frequency = self.base_frequency

            # Generate the new ding sound
            self.last_ding_time = current_time
            ding_sound = generate_ding(frequency=self.current_frequency, duration=self.ding_duration)

            # Stop the currently active stream
            active_stream_index = self.active_stream_index

            # Move to the next stream in the revolver
            self.active_stream_index = (self.active_stream_index + 1) % len(self.streams)
            next_stream_index = self.active_stream_index

            # Play the new sound on the next stream in a background thread
            threading.Thread(target=self._play_sound, args=(next_stream_index, ding_sound), daemon=True).start()

    def cleanup(self):
        """
        Clean up all streams and terminate PyAudio.
        """
        with self.lock:
            for stream in self.streams:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    print(f"Error closing stream: {e}")
            self.p.terminate()

# Callback for mouse click
def on_click(x, y, button, pressed):
    if pressed:
        audio_player.play_ding()

# Initialize the audio player
audio_player = AudioPlayer()

# Set up the mouse listener
try:
    with mouse.Listener(on_click=on_click) as listener:
        print("Listening for mouse clicks. Press Ctrl+C to exit.")
        listener.join()
finally:
    audio_player.cleanup()
