#!/usr/bin/env python3
"""
Terminal Notepad with Tabs
A lightweight terminal-based text editor with tab functionality.

Usage: python notepad.py [file1] [file2] ...

Controls:
- Ctrl+N: New tab
- Ctrl+O: Open file
- Ctrl+S: Save file
- Ctrl+W: Close tab
- Ctrl+Q: Quit
- Ctrl+Left/Right: Switch tabs
- Tab: Switch to next tab
- Arrow keys: Navigate text
- Page Up/Down: Scroll
- Home/End: Line navigation
"""

import curses
import os
import sys
from typing import List, Optional
import argparse


class TextBuffer:
    """Manages text content for a single tab."""
    
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        self.lines: List[str] = [""]
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_y = 0
        self.modified = False
        
        if filename and os.path.exists(filename):
            self.load_file()
    
    def load_file(self):
        """Load file content into buffer."""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                self.lines = f.read().splitlines()
                if not self.lines:
                    self.lines = [""]
            self.modified = False
        except Exception as e:
            self.lines = [f"Error loading file: {str(e)}"]
    
    def save_file(self, filename: Optional[str] = None):
        """Save buffer content to file."""
        if filename:
            self.filename = filename
        
        if not self.filename:
            return False
        
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.lines))
            self.modified = False
            return True
        except Exception:
            return False
    
    def insert_char(self, char: str):
        """Insert character at cursor position."""
        line = self.lines[self.cursor_y]
        self.lines[self.cursor_y] = line[:self.cursor_x] + char + line[self.cursor_x:]
        self.cursor_x += 1
        self.modified = True
    
    def delete_char(self):
        """Delete character before cursor (backspace)."""
        if self.cursor_x > 0:
            line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = line[:self.cursor_x-1] + line[self.cursor_x:]
            self.cursor_x -= 1
            self.modified = True
        elif self.cursor_y > 0:
            # Join with previous line
            self.cursor_x = len(self.lines[self.cursor_y - 1])
            self.lines[self.cursor_y - 1] += self.lines[self.cursor_y]
            del self.lines[self.cursor_y]
            self.cursor_y -= 1
            self.modified = True
    
    def delete_forward(self):
        """Delete character at cursor (delete key)."""
        line = self.lines[self.cursor_y]
        if self.cursor_x < len(line):
            self.lines[self.cursor_y] = line[:self.cursor_x] + line[self.cursor_x+1:]
            self.modified = True
        elif self.cursor_y < len(self.lines) - 1:
            # Join with next line
            self.lines[self.cursor_y] += self.lines[self.cursor_y + 1]
            del self.lines[self.cursor_y + 1]
            self.modified = True
    
    def insert_newline(self):
        """Insert new line at cursor position."""
        line = self.lines[self.cursor_y]
        self.lines[self.cursor_y] = line[:self.cursor_x]
        self.lines.insert(self.cursor_y + 1, line[self.cursor_x:])
        self.cursor_y += 1
        self.cursor_x = 0
        self.modified = True
    
    def move_cursor(self, dx: int, dy: int, max_x: int, max_y: int):
        """Move cursor with bounds checking."""
        new_y = max(0, min(len(self.lines) - 1, self.cursor_y + dy))
        new_x = max(0, min(len(self.lines[new_y]), self.cursor_x + dx))
        
        self.cursor_y = new_y
        self.cursor_x = new_x
        
        # Adjust scroll if needed
        if self.cursor_y < self.scroll_y:
            self.scroll_y = self.cursor_y
        elif self.cursor_y >= self.scroll_y + max_y:
            self.scroll_y = self.cursor_y - max_y + 1
    
    def get_display_name(self) -> str:
        """Get display name for tab."""
        name = os.path.basename(self.filename) if self.filename else "Untitled"
        return f"*{name}" if self.modified else name


class TerminalNotepad:
    """Main application class."""
    
    def __init__(self, initial_files: List[str] = None):
        self.tabs: List[TextBuffer] = []
        self.current_tab = 0
        
        # Initialize with files or empty tab
        if initial_files:
            for filename in initial_files:
                self.tabs.append(TextBuffer(filename))
        else:
            self.tabs.append(TextBuffer())
    
    def add_tab(self, filename: Optional[str] = None):
        """Add new tab."""
        self.tabs.append(TextBuffer(filename))
        self.current_tab = len(self.tabs) - 1
    
    def close_tab(self):
        """Close current tab."""
        if len(self.tabs) > 1:
            del self.tabs[self.current_tab]
            if self.current_tab >= len(self.tabs):
                self.current_tab = len(self.tabs) - 1
    
    def switch_tab(self, direction: int):
        """Switch to next/previous tab."""
        if len(self.tabs) > 1:
            self.current_tab = (self.current_tab + direction) % len(self.tabs)
    
    def get_current_buffer(self) -> TextBuffer:
        """Get currently active text buffer."""
        return self.tabs[self.current_tab]
    
    def draw_tabs(self, stdscr, width: int):
        """Draw tab bar at top of screen."""
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(0, 0, " " * width)
        
        x = 0
        for i, tab in enumerate(self.tabs):
            if x >= width - 20:  # Leave space for tab content
                break
                
            name = tab.get_display_name()
            if len(name) > 15:
                name = name[:12] + "..."
            
            # Highlight current tab
            if i == self.current_tab:
                stdscr.attron(curses.color_pair(2))
            else:
                stdscr.attron(curses.color_pair(1))
            
            tab_text = f" {name} "
            if x + len(tab_text) < width:
                stdscr.addstr(0, x, tab_text)
            x += len(tab_text) + 1
        
        stdscr.attroff(curses.color_pair(1))
        stdscr.attroff(curses.color_pair(2))
    
    def draw_content(self, stdscr, height: int, width: int):
        """Draw text content area."""
        buffer = self.get_current_buffer()
        
        # Draw text lines
        for i in range(height - 3):  # Reserve space for tabs and status
            line_num = buffer.scroll_y + i
            if line_num < len(buffer.lines):
                line = buffer.lines[line_num]
                if len(line) > width:
                    line = line[:width-1]
                stdscr.addstr(i + 1, 0, line)
            
            # Clear rest of line
            stdscr.clrtoeol()
    
    def draw_status(self, stdscr, height: int, width: int):
        """Draw status bar at bottom."""
        buffer = self.get_current_buffer()
        status = f" Line {buffer.cursor_y + 1}, Col {buffer.cursor_x + 1}"
        
        if buffer.filename:
            status += f" | {buffer.filename}"
        else:
            status += " | Untitled"
        
        if buffer.modified:
            status += " [Modified]"
        
        # Controls hint
        controls = " | Ctrl+N:New Ctrl+O:Open Ctrl+S:Save Ctrl+Q:Quit"
        if len(status + controls) < width:
            status += controls
        
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(height - 1, 0, status.ljust(width)[:width])
        stdscr.attroff(curses.color_pair(1))
    
    def handle_save(self, stdscr):
        """Handle save operation."""
        buffer = self.get_current_buffer()
        if not buffer.filename:
            # Get filename from user
            height, width = stdscr.getmaxyx()
            stdscr.addstr(height - 1, 0, "Save as: ".ljust(width))
            stdscr.refresh()
            
            curses.echo()
            filename = stdscr.getstr(height - 1, 9, width - 9).decode('utf-8')
            curses.noecho()
            
            if filename.strip():
                buffer.filename = filename.strip()
        
        if buffer.save_file():
            # Show success message briefly
            height, width = stdscr.getmaxyx()
            stdscr.addstr(height - 1, 0, f"Saved: {buffer.filename}".ljust(width))
            stdscr.refresh()
            curses.napms(1000)
    
    def handle_open(self, stdscr):
        """Handle open file operation."""
        height, width = stdscr.getmaxyx()
        stdscr.addstr(height - 1, 0, "Open file: ".ljust(width))
        stdscr.refresh()
        
        curses.echo()
        filename = stdscr.getstr(height - 1, 11, width - 11).decode('utf-8')
        curses.noecho()
        
        if filename.strip() and os.path.exists(filename.strip()):
            self.add_tab(filename.strip())
    
    def run(self, stdscr):
        """Main application loop."""
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)    # Status bar
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Active tab
        
        # Configure curses
        curses.curs_set(1)  # Show cursor
        stdscr.keypad(True)
        stdscr.timeout(100)  # Non-blocking input
        
        while True:
            height, width = stdscr.getmaxyx()
            stdscr.clear()
            
            # Draw interface
            self.draw_tabs(stdscr, width)
            self.draw_content(stdscr, height, width)
            self.draw_status(stdscr, height, width)
            
            # Position cursor
            buffer = self.get_current_buffer()
            cursor_screen_y = buffer.cursor_y - buffer.scroll_y + 1
            if 0 <= cursor_screen_y < height - 2:
                stdscr.move(cursor_screen_y, buffer.cursor_x)
            
            stdscr.refresh()
            
            # Handle input
            try:
                key = stdscr.getch()
            except:
                continue
            
            if key == -1:  # No input
                continue
            elif key == 17:  # Ctrl+Q
                break
            elif key == 14:  # Ctrl+N
                self.add_tab()
            elif key == 15:  # Ctrl+O
                self.handle_open(stdscr)
            elif key == 19:  # Ctrl+S
                self.handle_save(stdscr)
            elif key == 23:  # Ctrl+W
                self.close_tab()
            elif key == 9:   # Tab
                self.switch_tab(1)
            elif key == 560:  # Ctrl+Left
                self.switch_tab(-1)
            elif key == 545:  # Ctrl+Right
                self.switch_tab(1)
            elif key == curses.KEY_UP:
                buffer.move_cursor(0, -1, width, height - 3)
            elif key == curses.KEY_DOWN:
                buffer.move_cursor(0, 1, width, height - 3)
            elif key == curses.KEY_LEFT:
                buffer.move_cursor(-1, 0, width, height - 3)
            elif key == curses.KEY_RIGHT:
                buffer.move_cursor(1, 0, width, height - 3)
            elif key == curses.KEY_HOME:
                buffer.cursor_x = 0
            elif key == curses.KEY_END:
                buffer.cursor_x = len(buffer.lines[buffer.cursor_y])
            elif key == curses.KEY_PPAGE:  # Page Up
                buffer.move_cursor(0, -(height - 3), width, height - 3)
            elif key == curses.KEY_NPAGE:  # Page Down
                buffer.move_cursor(0, height - 3, width, height - 3)
            elif key == curses.KEY_BACKSPACE or key == 127:
                buffer.delete_char()
            elif key == curses.KEY_DC:  # Delete
                buffer.delete_forward()
            elif key == 10 or key == 13:  # Enter
                buffer.insert_newline()
            elif 32 <= key <= 126:  # Printable characters
                buffer.insert_char(chr(key))


def main():
    parser = argparse.ArgumentParser(description="Terminal Notepad with Tabs")
    parser.add_argument('files', nargs='*', help='Files to open')
    args = parser.parse_args()
    
    notepad = TerminalNotepad(args.files)
    
    try:
        curses.wrapper(notepad.run)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
