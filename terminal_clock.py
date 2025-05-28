#!/usr/bin/env python3
"""
Terminal Digital Clock with OCR-style ASCII font
A lightweight, real-time digital clock for the terminal
"""

import time
import sys
import os
from datetime import datetime

# OCR-style ASCII art digits (7-segment display inspired)
DIGITS = {
    '0': [
        " ███ ",
        "█   █",
        "█   █",
        "█   █",
        "█   █",
        "█   █",
        " ███ "
    ],
    '1': [
        "  █  ",
        " ██  ",
        "  █  ",
        "  █  ",
        "  █  ",
        "  █  ",
        " ███ "
    ],
    '2': [
        " ███ ",
        "█   █",
        "    █",
        " ███ ",
        "█    ",
        "█    ",
        "█████"
    ],
    '3': [
        " ███ ",
        "█   █",
        "    █",
        " ███ ",
        "    █",
        "█   █",
        " ███ "
    ],
    '4': [
        "█   █",
        "█   █",
        "█   █",
        "█████",
        "    █",
        "    █",
        "    █"
    ],
    '5': [
        "█████",
        "█    ",
        "█    ",
        "████ ",
        "    █",
        "█   █",
        " ███ "
    ],
    '6': [
        " ███ ",
        "█   █",
        "█    ",
        "████ ",
        "█   █",
        "█   █",
        " ███ "
    ],
    '7': [
        "█████",
        "    █",
        "   █ ",
        "  █  ",
        " █   ",
        "█    ",
        "█    "
    ],
    '8': [
        " ███ ",
        "█   █",
        "█   █",
        " ███ ",
        "█   █",
        "█   █",
        " ███ "
    ],
    '9': [
        " ███ ",
        "█   █",
        "█   █",
        " ████",
        "    █",
        "█   █",
        " ███ "
    ],
    ':': [
        "     ",
        "  █  ",
        "  █  ",
        "     ",
        "  █  ",
        "  █  ",
        "     "
    ],
    ' ': [
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        "     "
    ]
}

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_terminal_size():
    """Get terminal dimensions"""
    try:
        columns, rows = os.get_terminal_size()
        return columns, rows
    except OSError:
        return 80, 24  # Default fallback

def render_time_display(time_str):
    """Render the time string using ASCII art digits"""
    lines = [""] * 7
    
    for char in time_str:
        digit_lines = DIGITS.get(char, DIGITS[' '])
        for i in range(7):
            lines[i] += digit_lines[i] + " "
    
    return lines

def center_text(lines, width):
    """Center the ASCII art in the terminal"""
    centered_lines = []
    for line in lines:
        padding = (width - len(line)) // 2
        centered_lines.append(" " * padding + line)
    return centered_lines

def display_clock():
    """Main clock display function"""
    try:
        while True:
            # Get current time
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            
            # Clear screen and get terminal size
            clear_screen()
            width, height = get_terminal_size()
            
            # Render the time
            time_lines = render_time_display(time_str)
            centered_lines = center_text(time_lines, width)
            
            # Calculate vertical centering
            vertical_padding = (height - len(centered_lines)) // 2
            
            # Print vertical padding
            for _ in range(vertical_padding):
                print()
            
            # Print the centered clock
            for line in centered_lines:
                print(line)
            
            # Print some vertical padding at bottom
            for _ in range(vertical_padding):
                print()
            
            # Print instructions at bottom
            print(f"\n{' ' * ((width - 30) // 2)}Press Ctrl+C to exit")
            
            # Wait for next second
            time.sleep(1)
            
    except KeyboardInterrupt:
        clear_screen()
        print("\nClock terminated. Goodbye!")
        sys.exit(0)
    except Exception as e:
        clear_screen()
        print(f"Error: {e}")
        sys.exit(1)

def main():
    """Entry point for the clock application"""
    # Print welcome message
    clear_screen()
    print("Terminal Digital Clock")
    print("=====================")
    print("Starting clock... Press Ctrl+C to exit")
    time.sleep(1)
    
    # Start the clock display
    display_clock()

if __name__ == "__main__":
    main()
