from pynput import mouse
import numpy as np
import pyaudio
import threading

# Generate a "ding" sound in memory with a fade-out effect
def generate_ding(frequency=100.0, duration=0.2, volume=0.2, sample_rate=44100):
    """
    Generate a ding sound with a fade-out effect and return it as a numpy array.
    - frequency: Pitch of the ding in Hz (default: 880Hz).
    - duration: Duration of the ding in seconds (default: 1.3s).
    - volume: Volume of the ding (0.0 to 1.0, default: 0.5).
    - sample_rate: Sample rate in Hz (default: 44100Hz).
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)  # Time axis
    waveform = np.sin(2 * np.pi * frequency * t) * volume * 32767  # Sine wave
    fade_out = np.linspace(1, 0, len(waveform))  # Fade-out multiplier
    waveform = (waveform * fade_out).astype(np.int16)  # Apply fade-out and convert to 16-bit PCM
    return waveform

# Initialize PyAudio and preload the sound
class AudioPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=44100,
                                  output=True)
        self.ding_sound = generate_ding()
        self.current_thread = None
        self.lock = threading.Lock()
        
    def play_ding(self):
        def play():
            self.stream.write(self.ding_sound.tobytes())

        with self.lock:
            # Stop the current thread if it's running
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join(timeout=0.1)  # Wait briefly for it to stop
            
            # Start a new thread for playback
            self.current_thread = threading.Thread(target=play)
            self.current_thread.start()

    def cleanup(self):
        with self.lock:
            # Ensure any playing thread is stopped
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join()
        self.stream.stop_stream()
        self.stream.close()
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
