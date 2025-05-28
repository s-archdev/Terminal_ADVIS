# Terminal Digital Clock - Installation Guide

## Quick Installation

### Method 1: Direct Installation (Recommended)

1. **Save the script:**
   ```bash
   # Create a local bin directory if it doesn't exist
   mkdir -p ~/.local/bin
   
   # Save the clock script (replace with the path to your downloaded script)
   cp terminal_clock.py ~/.local/bin/tclock
   
   # Make it executable
   chmod +x ~/.local/bin/tclock
   ```

2. **Add to PATH (if not already added):**
   ```bash
   # Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   
   # Reload your shell or run:
   source ~/.bashrc
   ```

3. **Run the clock:**
   ```bash
   tclock
   ```

### Method 2: System-wide Installation (requires sudo)

1. **Copy to system directory:**
   ```bash
   sudo cp terminal_clock.py /usr/local/bin/tclock
   sudo chmod +x /usr/local/bin/tclock
   ```

2. **Run the clock:**
   ```bash
   tclock
   ```

### Method 3: Create an Alias

If you prefer to keep the original filename:

```bash
# Add to your shell profile
echo 'alias tclock="python3 /path/to/terminal_clock.py"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

Once installed, simply run:
```bash
tclock
```

The clock will display a large, OCR-style digital time that updates every second. Press `Ctrl+C` to exit.

## Features

- ✅ Real-time digital clock display
- ✅ OCR-style ASCII art font (7-segment display inspired)
- ✅ Automatic terminal centering
- ✅ Cross-platform compatible (Linux, macOS, Windows)
- ✅ Lightweight - no external dependencies
- ✅ Clean exit with Ctrl+C

## Requirements

- Python 3.x (usually pre-installed on most systems)
- Terminal with basic ANSI support

## Customization

You can modify the script to:
- Change the update interval (modify `time.sleep(1)`)
- Adjust the ASCII art style
- Add 12/24 hour format toggle
- Change colors (add ANSI color codes)
- Add date display

## Troubleshooting

**Permission denied:** Make sure the script is executable:
```bash
chmod +x /path/to/tclock
```

**Command not found:** Ensure the directory is in your PATH:
```bash
echo $PATH
```

**Python not found:** Make sure Python 3 is installed:
```bash
python3 --version
```
