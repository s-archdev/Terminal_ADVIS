#!/usr/bin/env python3
"""
Enhanced Interactive Pixelated GIF Terminal Player
A custom terminal application with playlist management, playback controls, and interactive features
"""

import os
import sys
import time
import argparse
import threading
import queue
import json
from PIL import Image, ImageSequence
import colorama
from colorama import Fore, Back, Style
import glob
import select
import tty
import termios

# Initialize colorama for cross-platform colored output
colorama.init()

class PlaybackState:
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

class PixelatedGifPlayer:
    def __init__(self, width=80, height=24, use_colors=True):
        self.width = width
        self.height = height
        self.use_colors = use_colors
        self.state = PlaybackState.STOPPED
        self.current_playlist = []
        self.current_index = 0
        self.current_frame = 0
        self.total_frames = 0
        self.frame_data = []
        self.frame_durations = []
        self.input_queue = queue.Queue()
        self.playback_thread = None
        self.input_thread = None
        self.loop_playlist = True
        self.loop_current = True
        
        # ASCII characters for different brightness levels
        self.ascii_chars = " .:-=+*#%@"
        
        # Color mapping for RGB to ANSI colors
        self.color_map = {
            (0, 0, 0): Back.BLACK,
            (255, 0, 0): Back.RED,
            (0, 255, 0): Back.GREEN,
            (255, 255, 0): Back.YELLOW,
            (0, 0, 255): Back.BLUE,
            (255, 0, 255): Back.MAGENTA,
            (0, 255, 255): Back.CYAN,
            (255, 255, 255): Back.WHITE,
        }
        
        # Save terminal settings for input handling
        self.old_settings = None

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def rgb_to_ascii(self, r, g, b):
        """Convert RGB values to ASCII character based on brightness"""
        brightness = int(0.299 * r + 0.587 * g + 0.114 * b)
        char_index = min(brightness * len(self.ascii_chars) // 256, len(self.ascii_chars) - 1)
        return self.ascii_chars[char_index]

    def get_closest_color(self, r, g, b):
        """Find the closest ANSI color to the given RGB"""
        min_distance = float('inf')
        closest_color = Back.BLACK
        
        for (cr, cg, cb), color_code in self.color_map.items():
            distance = ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_color = color_code
        
        return closest_color

    def process_frame(self, frame):
        """Convert a PIL Image frame to ASCII art"""
        frame = frame.resize((self.width, self.height), Image.Resampling.LANCZOS)
        frame = frame.convert('RGB')
        
        ascii_frame = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                r, g, b = frame.getpixel((x, y))
                
                if self.use_colors:
                    color = self.get_closest_color(r, g, b)
                    row += color + " " + Style.RESET_ALL
                else:
                    char = self.rgb_to_ascii(r, g, b)
                    row += char
            
            ascii_frame.append(row)
        
        return ascii_frame

    def load_gif(self, gif_path):
        """Load and process a GIF file"""
        try:
            with Image.open(gif_path) as img:
                frames = []
                durations = []
                
                for frame in ImageSequence.Iterator(img):
                    ascii_frame = self.process_frame(frame.copy())
                    frames.append(ascii_frame)
                    duration = frame.info.get('duration', 100) / 1000.0
                    durations.append(duration)
                
                return frames, durations
        except Exception as e:
            print(f"Error loading {gif_path}: {e}")
            return None, None

    def setup_input_handling(self):
        """Setup non-blocking input handling (Unix only)"""
        if os.name != 'nt':  # Unix/Linux/macOS
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())

    def restore_input_handling(self):
        """Restore terminal input settings"""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def input_handler(self):
        """Handle keyboard input in a separate thread"""
        while self.state != PlaybackState.STOPPED:
            try:
                if os.name == 'nt':  # Windows
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                        self.input_queue.put(key)
                else:  # Unix/Linux/macOS
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        self.input_queue.put(key)
                
                time.sleep(0.05)  # Small delay to prevent excessive CPU usage
            except:
                break

    def display_controls(self):
        """Display control information"""
        controls = [
            "Controls: [SPACE] Play/Pause | [N] Next | [P] Previous | [R] Restart | [L] Toggle Loop | [Q] Quit",
            f"Playlist: {self.current_index + 1}/{len(self.current_playlist)} | "
            f"Frame: {self.current_frame + 1}/{self.total_frames} | "
            f"State: {self.state.upper()} | Loop: {'ON' if self.loop_current else 'OFF'}"
        ]
        
        return controls

    def display_frame(self):
        """Display the current frame with controls"""
        self.clear_screen()
        
        # Display the GIF frame
        if self.frame_data and self.current_frame < len(self.frame_data):
            for line in self.frame_data[self.current_frame]:
                print(line)
        
        # Display controls and status
        print("\n" + "="*80)
        if self.current_playlist:
            current_gif = os.path.basename(self.current_playlist[self.current_index])
            print(f"Now Playing: {current_gif}")
        
        for control in self.display_controls():
            print(control)

    def process_input(self):
        """Process keyboard input"""
        try:
            while not self.input_queue.empty():
                key = self.input_queue.get_nowait()
                
                if key == ' ':  # Space - Play/Pause
                    if self.state == PlaybackState.PLAYING:
                        self.state = PlaybackState.PAUSED
                    elif self.state == PlaybackState.PAUSED:
                        self.state = PlaybackState.PLAYING
                
                elif key == 'n':  # Next GIF
                    self.next_gif()
                
                elif key == 'p':  # Previous GIF
                    self.previous_gif()
                
                elif key == 'r':  # Restart current GIF
                    self.current_frame = 0
                
                elif key == 'l':  # Toggle loop
                    self.loop_current = not self.loop_current
                
                elif key == 'q':  # Quit
                    self.state = PlaybackState.STOPPED
                    return False
        
        except queue.Empty:
            pass
        
        return True

    def next_gif(self):
        """Move to next GIF in playlist"""
        if self.current_playlist:
            self.current_index = (self.current_index + 1) % len(self.current_playlist)
            self.load_current_gif()

    def previous_gif(self):
        """Move to previous GIF in playlist"""
        if self.current_playlist:
            self.current_index = (self.current_index - 1) % len(self.current_playlist)
            self.load_current_gif()

    def load_current_gif(self):
        """Load the current GIF from the playlist"""
        if self.current_playlist and 0 <= self.current_index < len(self.current_playlist):
            gif_path = self.current_playlist[self.current_index]
            self.frame_data, self.frame_durations = self.load_gif(gif_path)
            if self.frame_data:
                self.total_frames = len(self.frame_data)
                self.current_frame = 0
                return True
        return False

    def playback_loop(self):
        """Main playback loop"""
        while self.state != PlaybackState.STOPPED:
            if not self.process_input():
                break
            
            if self.state == PlaybackState.PLAYING and self.frame_data:
                self.display_frame()
                
                # Wait for frame duration
                if self.current_frame < len(self.frame_durations):
                    time.sleep(self.frame_durations[self.current_frame])
                
                # Advance frame
                self.current_frame += 1
                
                # Handle end of GIF
                if self.current_frame >= self.total_frames:
                    if self.loop_current:
                        self.current_frame = 0
                    else:
                        # Move to next GIF in playlist
                        if len(self.current_playlist) > 1:
                            self.next_gif()
                        else:
                            self.state = PlaybackState.PAUSED
            
            elif self.state == PlaybackState.PAUSED:
                self.display_frame()
                time.sleep(0.1)
            
            else:
                time.sleep(0.1)

    def create_playlist(self, paths):
        """Create a playlist from given paths"""
        playlist = []
        
        for path in paths:
            if os.path.isfile(path) and path.lower().endswith(('.gif', '.GIF')):
                playlist.append(path)
            elif os.path.isdir(path):
                gif_files = self.find_gif_files(path)
                playlist.extend(gif_files)
        
        return playlist

    def find_gif_files(self, directory):
        """Find all GIF files in a directory"""
        gif_patterns = [
            os.path.join(directory, "*.gif"),
            os.path.join(directory, "*.GIF")
        ]
        
        gif_files = []
        for pattern in gif_patterns:
            gif_files.extend(glob.glob(pattern))
        
        return sorted(gif_files)

    def save_playlist(self, filename):
        """Save current playlist to a file"""
        try:
            playlist_data = {
                'playlist': self.current_playlist,
                'current_index': self.current_index
            }
            with open(filename, 'w') as f:
                json.dump(playlist_data, f, indent=2)
            print(f"Playlist saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving playlist: {e}")
            return False

    def load_playlist(self, filename):
        """Load playlist from a file"""
        try:
            with open(filename, 'r') as f:
                playlist_data = json.load(f)
            
            self.current_playlist = playlist_data.get('playlist', [])
            self.current_index = playlist_data.get('current_index', 0)
            
            # Verify files still exist
            valid_playlist = []
            for gif_path in self.current_playlist:
                if os.path.exists(gif_path):
                    valid_playlist.append(gif_path)
            
            self.current_playlist = valid_playlist
            if self.current_index >= len(self.current_playlist):
                self.current_index = 0
            
            print(f"Playlist loaded: {len(self.current_playlist)} GIFs")
            return True
        except Exception as e:
            print(f"Error loading playlist: {e}")
            return False

    def interactive_mode(self):
        """Start interactive mode with full controls"""
        if not self.current_playlist:
            print("No GIFs in playlist!")
            return
        
        print(f"Starting interactive mode with {len(self.current_playlist)} GIFs")
        print("Loading first GIF...")
        
        if not self.load_current_gif():
            print("Failed to load GIF!")
            return
        
        # Setup input handling
        try:
            self.setup_input_handling()
            
            # Start input handler thread
            self.input_thread = threading.Thread(target=self.input_handler, daemon=True)
            self.input_thread.start()
            
            # Start playback
            self.state = PlaybackState.PLAYING
            self.playback_loop()
        
        finally:
            self.restore_input_handling()
            self.clear_screen()
            print("Playback stopped.")

    def play_simple(self, loop=True):
        """Simple playback mode (original functionality)"""
        for i, gif_path in enumerate(self.current_playlist):
            print(f"\nNow playing: {os.path.basename(gif_path)} ({i+1}/{len(self.current_playlist)})")
            
            frame_data, frame_durations = self.load_gif(gif_path)
            if not frame_data:
                continue
            
            try:
                frame_index = 0
                while True:
                    self.clear_screen()
                    
                    # Display frame
                    for line in frame_data[frame_index]:
                        print(line)
                    
                    print(f"\nFrame {frame_index + 1}/{len(frame_data)} - {os.path.basename(gif_path)}")
                    print("Press Ctrl+C to skip to next GIF or stop")
                    
                    time.sleep(frame_durations[frame_index])
                    frame_index = (frame_index + 1) % len(frame_data)
                    
                    if frame_index == 0 and not loop:
                        break
            
            except KeyboardInterrupt:
                if i == len(self.current_playlist) - 1:  # Last GIF
                    break
                else:
                    continue


def main():
    parser = argparse.ArgumentParser(description="Enhanced Interactive Pixelated GIF Terminal Player")
    parser.add_argument("paths", nargs='*', help="Paths to GIF files or directories")
    parser.add_argument("-w", "--width", type=int, default=80, help="Terminal width (default: 80)")
    parser.add_argument("--height", type=int, default=24, help="Terminal height (default: 24)")
    parser.add_argument("--no-color", action="store_true", help="Use ASCII characters instead of colors")
    parser.add_argument("--simple", action="store_true", help="Use simple playback mode (no interactive controls)")
    parser.add_argument("--no-loop", action="store_true", help="Don't loop individual GIFs")
    parser.add_argument("--save-playlist", type=str, help="Save playlist to file")
    parser.add_argument("--load-playlist", type=str, help="Load playlist from file")
    
    args = parser.parse_args()
    
    # Create player instance
    player = PixelatedGifPlayer(
        width=args.width,
        height=args.height,
        use_colors=not args.no_color
    )
    
    try:
        # Handle playlist loading
        if args.load_playlist:
            if player.load_playlist(args.load_playlist):
                if args.paths:
                    # Add additional paths to loaded playlist
                    additional_playlist = player.create_playlist(args.paths)
                    player.current_playlist.extend(additional_playlist)
            else:
                return
        else:
            # Create playlist from arguments or default
            if not args.paths:
                default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gifs")
                if os.path.exists(default_path):
                    args.paths = [default_path]
                else:
                    print("No paths provided and no default gifs directory found.")
                    print(f"Please provide paths or add GIF files to: {default_path}")
                    return
            
            player.current_playlist = player.create_playlist(args.paths)
        
        if not player.current_playlist:
            print("No GIF files found!")
            return
        
        # Save playlist if requested
        if args.save_playlist:
            player.save_playlist(args.save_playlist)
        
        # Display playlist info
        print(f"Playlist created with {len(player.current_playlist)} GIFs:")
        for i, gif in enumerate(player.current_playlist[:5]):  # Show first 5
            print(f"  {i+1}. {os.path.basename(gif)}")
        if len(player.current_playlist) > 5:
            print(f"  ... and {len(player.current_playlist) - 5} more")
        
        print()
        
        # Set loop preference
        player.loop_current = not args.no_loop
        
        # Start playback
        if args.simple:
            print("Starting simple playback mode...")
            time.sleep(1)
            player.play_simple(loop=not args.no_loop)
        else:
            print("Starting interactive mode...")
            print("Use SPACE to play/pause, N/P for next/previous, Q to quit")
            time.sleep(2)
            player.interactive_mode()
    
    except KeyboardInterrupt:
        player.clear_screen()
        print("\nStopped by user")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()