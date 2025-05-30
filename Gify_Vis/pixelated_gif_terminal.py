#!/usr/bin/env python3
"""
Pixelated GIF Terminal Player
A custom terminal application that displays GIFs as pixelated ASCII art
"""

import os
import sys
import time
import argparse
from PIL import Image, ImageSequence
import colorama
from colorama import Fore, Back, Style
import threading
import glob

# Initialize colorama for cross-platform colored output
colorama.init()

class PixelatedGifPlayer:
    def __init__(self, width=80, height=24, use_colors=True):
        self.width = width
        self.height = height
        self.use_colors = use_colors
        self.running = False
        
        # ASCII characters for different brightness levels (darkest to lightest)
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
        # Resize frame to fit terminal
        frame = frame.resize((self.width, self.height), Image.Resampling.LANCZOS)
        frame = frame.convert('RGB')
        
        ascii_frame = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                r, g, b = frame.getpixel((x, y))
                
                if self.use_colors:
                    # Use colored blocks
                    color = self.get_closest_color(r, g, b)
                    row += color + " " + Style.RESET_ALL
                else:
                    # Use ASCII characters
                    char = self.rgb_to_ascii(r, g, b)
                    row += char
            
            ascii_frame.append(row)
        
        return ascii_frame

    def play_gif(self, gif_path, loop=True):
        """Play a single GIF file"""
        try:
            with Image.open(gif_path) as img:
                frames = []
                durations = []
                
                # Process all frames
                for frame in ImageSequence.Iterator(img):
                    ascii_frame = self.process_frame(frame.copy())
                    frames.append(ascii_frame)
                    
                    # Get frame duration (default to 100ms if not specified)
                    duration = frame.info.get('duration', 100) / 1000.0
                    durations.append(duration)
                
                print(f"Loaded {len(frames)} frames from {os.path.basename(gif_path)}")
                print("Press Ctrl+C to stop\n")
                
                self.running = True
                frame_index = 0
                
                while self.running and (loop or frame_index < len(frames)):
                    self.clear_screen()
                    
                    # Display current frame
                    for line in frames[frame_index]:
                        print(line)
                    
                    print(f"\nFrame {frame_index + 1}/{len(frames)} - {os.path.basename(gif_path)}")
                    
                    # Wait for frame duration
                    time.sleep(durations[frame_index])
                    
                    frame_index = (frame_index + 1) % len(frames)
                    
                    if not loop and frame_index == 0:
                        break
                        
        except Exception as e:
            print(f"Error playing {gif_path}: {e}")

    def play_multiple_gifs(self, gif_paths, loop=True):
        """Play multiple GIF files in sequence"""
        while loop:
            for gif_path in gif_paths:
                if not self.running:
                    break
                print(f"\nNow playing: {os.path.basename(gif_path)}")
                time.sleep(1)
                self.play_gif(gif_path, loop=False)
            
            if not loop:
                break

    def stop(self):
        """Stop the player"""
        self.running = False


def find_gif_files(directory):
    """Find all GIF files in a directory"""
    gif_patterns = [
        os.path.join(directory, "*.gif"),
        os.path.join(directory, "*.GIF")
    ]
    
    gif_files = []
    for pattern in gif_patterns:
        gif_files.extend(glob.glob(pattern))
    
    return sorted(gif_files)


def main():
    parser = argparse.ArgumentParser(description="Pixelated GIF Terminal Player")
    parser.add_argument("path", help="Path to GIF file or directory containing GIFs")
    parser.add_argument("-w", "--width", type=int, default=80, help="Terminal width (default: 80)")
    parser.add_argument("-h", "--height", type=int, default=24, help="Terminal height (default: 24)")
    parser.add_argument("--no-color", action="store_true", help="Use ASCII characters instead of colors")
    parser.add_argument("--no-loop", action="store_true", help="Play once instead of looping")
    
    args = parser.parse_args()
    
    # Create player instance
    player = PixelatedGifPlayer(
        width=args.width,
        height=args.height,
        use_colors=not args.no_color
    )
    
    try:
        if os.path.isfile(args.path):
            # Single file
            if args.path.lower().endswith(('.gif', '.GIF')):
                player.play_gif(args.path, loop=not args.no_loop)
            else:
                print("Error: File must be a GIF")
                sys.exit(1)
        
        elif os.path.isdir(args.path):
            # Directory with multiple GIFs
            gif_files = find_gif_files(args.path)
            
            if not gif_files:
                print(f"No GIF files found in {args.path}")
                sys.exit(1)
            
            print(f"Found {len(gif_files)} GIF files:")
            for gif in gif_files:
                print(f"  - {os.path.basename(gif)}")
            
            time.sleep(2)
            player.play_multiple_gifs(gif_files, loop=not args.no_loop)
        
        else:
            print(f"Error: Path {args.path} does not exist")
            sys.exit(1)
    
    except KeyboardInterrupt:
        player.stop()
        player.clear_screen()
        print("\nStopped by user")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()