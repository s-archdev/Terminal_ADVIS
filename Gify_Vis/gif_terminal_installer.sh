#!/bin/bash

# Pixelated GIF Terminal Player Installer
# This script installs the GIF terminal player and its dependencies

set -e

echo "🎬 Pixelated GIF Terminal Player Installer"
echo "=========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Python 3 is installed
check_python() {
    print_step "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_status "Python 3 found: $PYTHON_VERSION"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        if [[ $PYTHON_VERSION == 3.* ]]; then
            print_status "Python 3 found: $PYTHON_VERSION"
            PYTHON_CMD="python"
        else
            print_error "Python 3 is required. Found Python $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    print_step "Checking pip installation..."
    
    if command -v pip3 &> /dev/null; then
        print_status "pip3 found"
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        print_status "pip found"
        PIP_CMD="pip"
    else
        print_error "pip is not installed. Please install pip first."
        exit 1
    fi
}

# Install Python dependencies
install_dependencies() {
    print_step "Installing Python dependencies..."
    
    DEPENDENCIES=("Pillow" "colorama")
    
    for dep in "${DEPENDENCIES[@]}"; do
        print_status "Installing $dep..."
        $PIP_CMD install "$dep" --user
    done
    
    print_status "All dependencies installed successfully!"
}

# Create installation directory
create_install_dir() {
    print_step "Creating installation directory..."
    
    INSTALL_DIR="$HOME/.gif-terminal"
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/gifs"
    
    print_status "Installation directory created: $INSTALL_DIR"
}

# Download or copy the main script
install_main_script() {
    print_step "Installing main script..."
    
    # Create the main script file
    cat > "$INSTALL_DIR/gif-player.py" << 'EOL'
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
    parser.add_argument("path", nargs='?', default=None, help="Path to GIF file or directory containing GIFs")
    parser.add_argument("-w", "--width", type=int, default=80, help="Terminal width (default: 80)")
    parser.add_argument("--height", type=int, default=24, help="Terminal height (default: 24)")
    parser.add_argument("--no-color", action="store_true", help="Use ASCII characters instead of colors")
    parser.add_argument("--no-loop", action="store_true", help="Play once instead of looping")
    
    args = parser.parse_args()
    
    # If no path provided, use the default gifs directory
    if args.path is None:
        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gifs")
        if os.path.exists(default_path):
            args.path = default_path
        else:
            print("No path provided and no default gifs directory found.")
            print(f"Please provide a path or add GIF files to: {default_path}")
            sys.exit(1)
    
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
                print("Please add some GIF files to the directory and try again.")
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
EOL

    chmod +x "$INSTALL_DIR/gif-player.py"
    print_status "Main script installed successfully!"
}

# Create wrapper script for easy execution
create_wrapper_script() {
    print_step "Creating wrapper script..."
    
    cat > "$INSTALL_DIR/gif-terminal" << EOL
#!/bin/bash
# Wrapper script for the GIF Terminal Player

cd "$INSTALL_DIR"
$PYTHON_CMD gif-player.py "\$@"
EOL

    chmod +x "$INSTALL_DIR/gif-terminal"
    print_status "Wrapper script created!"
}

# Add to PATH
setup_path() {
    print_step "Setting up PATH..."
    
    # Check if already in PATH
    if [[ ":$PATH:" == *":$INSTALL_DIR:"* ]]; then
        print_status "Already in PATH"
        return
    fi
    
    # Add to .bashrc or .zshrc
    SHELL_RC=""
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
    elif [[ "$SHELL" == *"bash"* ]]; then
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_RC="$HOME/.bashrc"  # Default to bashrc
    fi
    
    echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
    print_status "Added to PATH in $SHELL_RC"
    print_warning "Please restart your terminal or run: source $SHELL_RC"
}

# Create sample README
create_readme() {
    print_step "Creating README..."
    
    cat > "$INSTALL_DIR/README.md" << 'EOL'
# Pixelated GIF Terminal Player

A fun terminal application that displays GIFs as pixelated ASCII art!

## Usage

### Play a single GIF:
```bash
gif-terminal path/to/your/image.gif
```

### Play all GIFs in a directory:
```bash
gif-terminal path/to/gif/directory/
```

### Play GIFs from the default directory:
```bash
gif-terminal
```
(This will play all GIFs in the `gifs/` folder)

## Options

- `-w, --width`: Set terminal width (default: 80)
- `--height`: Set terminal height (default: 24)
- `--no-color`: Use ASCII characters instead of colors
- `--no-loop`: Play once instead of looping

## Examples

```bash
# Play with custom size
gif-terminal my-gif.gif -w 120 --height 30

# Play without colors (ASCII only)
gif-terminal my-gif.gif --no-color

# Play once without looping
gif-terminal my-gif.gif --no-loop
```

## Adding GIFs

Simply copy your GIF files to the `gifs/` directory and run `gif-terminal` to play them all!

## Tips

- Smaller, simpler GIFs work best
- Use a terminal with good color support for the best experience
- Press Ctrl+C to stop playback
- Try different terminal sizes for different effects

Enjoy your pixelated GIF terminal! 🎬
EOL

    print_status "README created!"
}

# Main installation function
main() {
    echo "Starting installation..."
    echo
    
    check_python
    check_pip
    install_dependencies
    create_install_dir
    install_main_script
    create_wrapper_script
    setup_path
    create_readme
    
    echo
    echo "🎉 Installation completed successfully!"
    echo
    echo "📁 Installation directory: $INSTALL_DIR"
    echo "🎬 Add your GIF files to: $INSTALL_DIR/gifs/"
    echo
    echo "Usage:"
    echo "  gif-terminal                    # Play all GIFs in the gifs/ folder"
    echo "  gif-terminal path/to/file.gif   # Play a specific GIF"
    echo "  gif-terminal path/to/directory/ # Play all GIFs in a directory"
    echo
    echo "⚠️  Please restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
    echo
    echo "Have fun with your pixelated GIF terminal! 🚀"
}

# Run the installation
main