#!/usr/bin/env python3
"""
Enhanced Terminal Notepad with Tabs
A lightweight terminal-based text editor with advanced features.

Usage: python notepad.py [file1] [file2] ...

Controls:
- Ctrl+N: New tab
- Ctrl+O: Open file
- Ctrl+S: Save file
- Ctrl+W: Close tab
- Ctrl+Q: Quit
- Ctrl+F: Find/Search
- Ctrl+G: Go to line
- Ctrl+T: Toggle theme
- Ctrl+H: Toggle syntax highlighting
- Ctrl+Left/Right: Switch tabs
- Tab: Switch to next tab
- F3: Find next
- Esc: Cancel search/goto
- Arrow keys: Navigate text
- Page Up/Down: Scroll
- Home/End: Line navigation
"""

import curses
import os
import sys
import re
from typing import List, Optional, Dict, Tuple
import argparse


class SyntaxHighlighter:
    """Handles syntax highlighting for various file types."""
    
    def __init__(self):
        self.patterns = {
            'python': [
                (r'\b(def|class|if|elif|else|for|while|try|except|finally|with|import|from|return|yield|lambda|pass|break|continue|and|or|not|in|is|True|False|None)\b', 1),  # Keywords
                (r'#.*$', 2),  # Comments
                (r'["\'].*?["\']', 3),  # Strings
                (r'\b\d+\b', 4),  # Numbers
                (r'\b(self|cls)\b', 5),  # Special
            ],
            'javascript': [
                (r'\b(function|var|let|const|if|else|for|while|do|switch|case|default|try|catch|finally|return|break|continue|true|false|null|undefined)\b', 1),
                (r'//.*$', 2),
                (r'/\*.*?\*/', 2),
                (r'["\'].*?["\']', 3),
                (r'\b\d+\b', 4),
                (r'\b(this|window|document)\b', 5),
            ],
            'c': [
                (r'\b(int|char|float|double|void|if|else|for|while|do|switch|case|default|return|break|continue|struct|typedef|enum|static|extern|const|volatile)\b', 1),
                (r'//.*$', 2),
                (r'/\*.*?\*/', 2),
                (r'".*?"', 3),
                (r'\b\d+\b', 4),
                (r'#\w+', 5),
            ],
            'html': [
                (r'</?[^>]+>', 1),  # Tags
                (r'<!--.*?-->', 2),  # Comments
                (r'["\'].*?["\']', 3),  # Attributes
            ],
            'css': [
                (r'[.#]?\w+\s*{', 1),  # Selectors
                (r'/\*.*?\*/', 2),  # Comments
                (r':\s*[^;]+;', 3),  # Properties
                (r'["\'].*?["\']', 3),  # Strings
            ],
            'markdown': [
                (r'^#{1,6}\s.*$', 1),  # Headers
                (r'\*\*.*?\*\*', 3),  # Bold
                (r'\*.*?\*', 4),  # Italic
                (r'`.*?`', 5),  # Code
                (r'\[.*?\]\(.*?\)', 1),  # Links
            ]
        }
    
    def get_file_type(self, filename: str) -> str:
        """Determine file type from extension."""
        if not filename:
            return 'text'
        
        ext = os.path.splitext(filename)[1].lower()
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.c': 'c', '.h': 'c', '.cpp': 'c', '.hpp': 'c',
            '.html': 'html', '.htm': 'html',
            '.css': 'css',
            '.md': 'markdown', '.markdown': 'markdown',
        }
        return ext_map.get(ext, 'text')
    
    def highlight_line(self, line: str, file_type: str) -> List[Tuple[str, int]]:
        """Return list of (text, color_pair) tuples for a line."""
        if file_type not in self.patterns:
            return [(line, 0)]
        
        result = []
        pos = 0
        
        # Find all matches for all patterns
        matches = []
        for pattern, color in self.patterns[file_type]:
            for match in re.finditer(pattern, line, re.MULTILINE):
                matches.append((match.start(), match.end(), color))
        
        # Sort matches by position
        matches.sort(key=lambda x: x[0])
        
        # Remove overlapping matches (keep first)
        filtered = []
        for start, end, color in matches:
            if not any(s <= start < e for s, e, _ in filtered):
                filtered.append((start, end, color))
        
        # Build result
        for start, end, color in filtered:
            if start > pos:
                result.append((line[pos:start], 0))
            result.append((line[start:end], color))
            pos = end
        
        if pos < len(line):
            result.append((line[pos:], 0))
        
        return result if result else [(line, 0)]


class SearchManager:
    """Handles search functionality."""
    
    def __init__(self):
        self.query = ""
        self.matches = []
        self.current_match = -1
        self.case_sensitive = False
    
    def search(self, lines: List[str], query: str, case_sensitive: bool = False):
        """Find all matches of query in text."""
        self.query = query
        self.case_sensitive = case_sensitive
        self.matches = []
        
        if not query:
            return
        
        pattern = query if case_sensitive else query.lower()
        
        for line_num, line in enumerate(lines):
            search_line = line if case_sensitive else line.lower()
            pos = 0
            while True:
                pos = search_line.find(pattern, pos)
                if pos == -1:
                    break
                self.matches.append((line_num, pos, pos + len(query)))
                pos += 1
    
    def next_match(self, current_line: int, current_col: int) -> Optional[Tuple[int, int]]:
        """Find next match after current position."""
        if not self.matches:
            return None
        
        for i, (line, start, end) in enumerate(self.matches):
            if line > current_line or (line == current_line and start > current_col):
                self.current_match = i
                return (line, start)
        
        # Wrap to beginning
        if self.matches:
            self.current_match = 0
            return (self.matches[0][0], self.matches[0][1])
        
        return None
    
    def get_current_match(self) -> Optional[Tuple[int, int, int]]:
        """Get current match info."""
        if 0 <= self.current_match < len(self.matches):
            return self.matches[self.current_match]
        return None


class Theme:
    """Color theme management."""
    
    def __init__(self):
        self.themes = {
            'default': {
                'tab_bar': (curses.COLOR_BLACK, curses.COLOR_CYAN),
                'active_tab': (curses.COLOR_BLACK, curses.COLOR_WHITE),
                'status_bar': (curses.COLOR_BLACK, curses.COLOR_CYAN),
                'text': (curses.COLOR_WHITE, curses.COLOR_BLACK),
                'keyword': (curses.COLOR_YELLOW, curses.COLOR_BLACK),
                'comment': (curses.COLOR_GREEN, curses.COLOR_BLACK),
                'string': (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
                'number': (curses.COLOR_CYAN, curses.COLOR_BLACK),
                'special': (curses.COLOR_RED, curses.COLOR_BLACK),
                'search_highlight': (curses.COLOR_BLACK, curses.COLOR_YELLOW),
            },
            'dark': {
                'tab_bar': (curses.COLOR_WHITE, curses.COLOR_BLACK),
                'active_tab': (curses.COLOR_BLACK, curses.COLOR_WHITE),
                'status_bar': (curses.COLOR_WHITE, curses.COLOR_BLACK),
                'text': (curses.COLOR_WHITE, curses.COLOR_BLACK),
                'keyword': (curses.COLOR_BLUE, curses.COLOR_BLACK),
                'comment': (curses.COLOR_GREEN, curses.COLOR_BLACK),
                'string': (curses.COLOR_RED, curses.COLOR_BLACK),
                'number': (curses.COLOR_CYAN, curses.COLOR_BLACK),
                'special': (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
                'search_highlight': (curses.COLOR_BLACK, curses.COLOR_YELLOW),
            },
            'light': {
                'tab_bar': (curses.COLOR_BLACK, curses.COLOR_WHITE),
                'active_tab': (curses.COLOR_WHITE, curses.COLOR_BLACK),
                'status_bar': (curses.COLOR_BLACK, curses.COLOR_WHITE),
                'text': (curses.COLOR_BLACK, curses.COLOR_WHITE),
                'keyword': (curses.COLOR_BLUE, curses.COLOR_WHITE),
                'comment': (curses.COLOR_GREEN, curses.COLOR_WHITE),
                'string': (curses.COLOR_RED, curses.COLOR_WHITE),
                'number': (curses.COLOR_MAGENTA, curses.COLOR_WHITE),
                'special': (curses.COLOR_CYAN, curses.COLOR_WHITE),
                'search_highlight': (curses.COLOR_WHITE, curses.COLOR_BLUE),
            }
        }
        self.current_theme = 'default'
        self.color_pairs = {}
    
    def init_colors(self):
        """Initialize color pairs."""
        curses.start_color()
        pair_num = 1
        
        for theme_name, theme in self.themes.items():
            self.color_pairs[theme_name] = {}
            for element, (fg, bg) in theme.items():
                curses.init_pair(pair_num, fg, bg)
                self.color_pairs[theme_name][element] = pair_num
                pair_num += 1
    
    def get_color(self, element: str) -> int:
        """Get color pair for element in current theme."""
        return self.color_pairs[self.current_theme].get(element, 0)
    
    def next_theme(self):
        """Switch to next theme."""
        themes = list(self.themes.keys())
        current_idx = themes.index(self.current_theme)
        self.current_theme = themes[(current_idx + 1) % len(themes)]


class TextBuffer:
    """Enhanced text buffer with search and highlighting support."""
    
    def __init__(self, filename: Optional[str] = None):
        self.filename = filename
        self.lines: List[str] = [""]
        self.cursor_x = 0
        self.cursor_y = 0
        self.scroll_y = 0
        self.modified = False
        self.file_type = 'text'
        
        if filename and os.path.exists(filename):
            self.load_file()
        
        if filename:
            self.file_type = SyntaxHighlighter().get_file_type(filename)
    
    def load_file(self):
        """Load file content into buffer."""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                content = f.read()
                self.lines = content.splitlines() if content else [""]
                if not self.lines:
                    self.lines = [""]
            self.modified = False
        except Exception as e:
            self.lines = [f"Error loading file: {str(e)}"]
    
    def save_file(self, filename: Optional[str] = None):
        """Save buffer content to file."""
        if filename:
            self.filename = filename
            self.file_type = SyntaxHighlighter().get_file_type(filename)
        
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
    
    def goto_line(self, line_num: int, max_y: int):
        """Go to specific line number."""
        target_line = max(0, min(len(self.lines) - 1, line_num - 1))
        self.cursor_y = target_line
        self.cursor_x = 0
        
        # Center the line on screen if possible
        if target_line >= max_y // 2:
            self.scroll_y = max(0, target_line - max_y // 2)
        else:
            self.scroll_y = 0
    
    def get_display_name(self) -> str:
        """Get display name for tab."""
        name = os.path.basename(self.filename) if self.filename else "Untitled"
        return f"*{name}" if self.modified else name


class TerminalNotepad:
    """Enhanced main application class."""
    
    def __init__(self, initial_files: List[str] = None):
        self.tabs: List[TextBuffer] = []
        self.current_tab = 0
        self.syntax_highlighter = SyntaxHighlighter()
        self.search_manager = SearchManager()
        self.theme = Theme()
        self.syntax_enabled = True
        self.search_mode = False
        self.goto_mode = False
        
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
        stdscr.attron(curses.color_pair(self.theme.get_color('tab_bar')))
        stdscr.addstr(0, 0, " " * width)
        
        x = 0
        for i, tab in enumerate(self.tabs):
            if x >= width - 20:
                break
                
            name = tab.get_display_name()
            if len(name) > 15:
                name = name[:12] + "..."
            
            # Highlight current tab
            if i == self.current_tab:
                stdscr.attron(curses.color_pair(self.theme.get_color('active_tab')))
            else:
                stdscr.attron(curses.color_pair(self.theme.get_color('tab_bar')))
            
            tab_text = f" {name} "
            if x + len(tab_text) < width:
                stdscr.addstr(0, x, tab_text)
            x += len(tab_text) + 1
        
        stdscr.attroff(curses.color_pair(self.theme.get_color('tab_bar')))
        stdscr.attroff(curses.color_pair(self.theme.get_color('active_tab')))
    
    def draw_content(self, stdscr, height: int, width: int):
        """Draw text content area with syntax highlighting."""
        buffer = self.get_current_buffer()
        
        # Get search highlight info
        search_match = self.search_manager.get_current_match()
        
        for i in range(height - 3):
            line_num = buffer.scroll_y + i
            if line_num < len(buffer.lines):
                line = buffer.lines[line_num]
                
                if self.syntax_enabled and buffer.file_type != 'text':
                    # Apply syntax highlighting
                    segments = self.syntax_highlighter.highlight_line(line, buffer.file_type)
                    x = 0
                    for text, color_type in segments:
                        if x >= width:
                            break
                        
                        # Get appropriate color
                        if color_type == 0:
                            color = self.theme.get_color('text')
                        elif color_type == 1:
                            color = self.theme.get_color('keyword')
                        elif color_type == 2:
                            color = self.theme.get_color('comment')
                        elif color_type == 3:
                            color = self.theme.get_color('string')
                        elif color_type == 4:
                            color = self.theme.get_color('number')
                        elif color_type == 5:
                            color = self.theme.get_color('special')
                        else:
                            color = self.theme.get_color('text')
                        
                        # Check for search highlight
                        if (search_match and search_match[0] == line_num and 
                            x <= search_match[1] < x + len(text)):
                            color = self.theme.get_color('search_highlight')
                        
                        stdscr.attron(curses.color_pair(color))
                        display_text = text[:width - x]
                        stdscr.addstr(i + 1, x, display_text)
                        stdscr.attroff(curses.color_pair(color))
                        x += len(display_text)
                else:
                    # No highlighting
                    display_line = line[:width]
                    
                    # Check for search highlight
                    if (search_match and search_match[0] == line_num):
                        start, end = search_match[1], search_match[2]
                        if start < len(display_line):
                            # Before match
                            if start > 0:
                                stdscr.addstr(i + 1, 0, display_line[:start])
                            # Match
                            stdscr.attron(curses.color_pair(self.theme.get_color('search_highlight')))
                            stdscr.addstr(i + 1, start, display_line[start:min(end, len(display_line))])
                            stdscr.attroff(curses.color_pair(self.theme.get_color('search_highlight')))
                            # After match
                            if end < len(display_line):
                                stdscr.addstr(i + 1, end, display_line[end:])
                        else:
                            stdscr.addstr(i + 1, 0, display_line)
                    else:
                        stdscr.addstr(i + 1, 0, display_line)
            
            stdscr.clrtoeol()
    
    def draw_status(self, stdscr, height: int, width: int):
        """Draw status bar at bottom."""
        buffer = self.get_current_buffer()
        
        if self.search_mode:
            status = f" Search: {self.search_manager.query}"
            if self.search_manager.matches:
                status += f" ({self.search_manager.current_match + 1}/{len(self.search_manager.matches)})"
        elif self.goto_mode:
            status = " Go to line: "
        else:
            status = f" Ln {buffer.cursor_y + 1}, Col {buffer.cursor_x + 1}"
            
            if buffer.filename:
                status += f" | {buffer.filename}"
            else:
                status += " | Untitled"
            
            if buffer.modified:
                status += " [Modified]"
            
            status += f" | {buffer.file_type.upper()}"
            status += f" | Theme: {self.theme.current_theme}"
            
            if not self.syntax_enabled:
                status += " [No Syntax]"
        
        stdscr.attron(curses.color_pair(self.theme.get_color('status_bar')))
        stdscr.addstr(height - 1, 0, status.ljust(width)[:width])
        stdscr.attroff(curses.color_pair(self.theme.get_color('status_bar')))
    
    def handle_search(self, stdscr):
        """Handle search input."""
        height, width = stdscr.getmaxyx()
        buffer = self.get_current_buffer()
        
        query = ""
        self.search_mode = True
        
        while True:
            # Update display
            stdscr.clear()
            self.draw_tabs(stdscr, width)
            self.draw_content(stdscr, height, width)
            
            # Show search prompt
            prompt = f" Search: {query}"
            stdscr.attron(curses.color_pair(self.theme.get_color('status_bar')))
            stdscr.addstr(height - 1, 0, prompt.ljust(width)[:width])
            stdscr.attroff(curses.color_pair(self.theme.get_color('status_bar')))
            stdscr.move(height - 1, len(prompt))
            stdscr.refresh()
            
            key = stdscr.getch()
            
            if key == 27:  # Escape
                break
            elif key == 10 or key == 13:  # Enter
                if query:
                    self.search_manager.search(buffer.lines, query)
                    if self.search_manager.matches:
                        match = self.search_manager.next_match(buffer.cursor_y, buffer.cursor_x)
                        if match:
                            buffer.cursor_y, buffer.cursor_x = match
                            buffer.move_cursor(0, 0, width, height - 3)  # Adjust scroll
                break
            elif key == curses.KEY_BACKSPACE or key == 127:
                query = query[:-1]
            elif 32 <= key <= 126:
                query += chr(key)
        
        self.search_mode = False
    
    def handle_goto(self, stdscr):
        """Handle go to line input."""
        height, width = stdscr.getmaxyx()
        buffer = self.get_current_buffer()
        
        line_str = ""
        self.goto_mode = True
        
        while True:
            # Update display
            stdscr.clear()
            self.draw_tabs(stdscr, width)
            self.draw_content(stdscr, height, width)
            
            # Show goto prompt
            prompt = f" Go to line: {line_str}"
            stdscr.attron(curses.color_pair(self.theme.get_color('status_bar')))
            stdscr.addstr(height - 1, 0, prompt.ljust(width)[:width])
            stdscr.attroff(curses.color_pair(self.theme.get_color('status_bar')))
            stdscr.move(height - 1, len(prompt))
            stdscr.refresh()
            
            key = stdscr.getch()
            
            if key == 27:  # Escape
                break
            elif key == 10 or key == 13:  # Enter
                try:
                    line_num = int(line_str)
                    buffer.goto_line(line_num, height - 3)
                except ValueError:
                    pass
                break
            elif key == curses.KEY_BACKSPACE or key == 127:
                line_str = line_str[:-1]
            elif 48 <= key <= 57:  # Digits only
                line_str += chr(key)
        
        self.goto_mode = False
    
    def handle_save(self, stdscr):
        """Handle save operation."""
        buffer = self.get_current_buffer()
        if not buffer.filename:
            height, width = stdscr.getmaxyx()
            stdscr.addstr(height - 1, 0, "Save as: ".ljust(width))
            stdscr.refresh()
            
            curses.echo()
            filename = stdscr.getstr(height - 1, 9, width - 9).decode('utf-8')
            curses.noecho()
            
            if filename.strip():
                buffer.filename = filename.strip()
        
        if buffer.save_file():
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
        self.theme.init_colors()
        
        # Configure curses
        curses.curs_set(1)
        stdscr.keypad(True)
        stdscr.timeout(100)
        
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
                stdscr.move(cursor_screen_y, min(buffer.cursor_x, width - 1))
            
            stdscr.refresh()
            
            # Handle input
            try:
                key = stdscr.getch()
            except:
                continue
            
            if key == -1:
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
            elif key == 6:   # Ctrl+F
                self.handle_search(stdscr)
            elif key == 7:   # Ctrl+G
                self.handle_goto(stdscr)
            elif key == 20:  # Ctrl+T
                self.theme.next_theme()
            elif key == 8:   # Ctrl+H
                self.syntax_enabled = not self.syntax_enabled
            elif key == curses.KEY_F3:  # F3 - Find next
                if self.search_manager.matches:
                    match = self.search_manager.next_match(buffer.cursor_y, buffer.cursor_x)
                    if match:
                        buffer.cursor_y, buffer.cursor_x = match
                        buffer.move_cursor(0, 0, width, height - 3)
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
    parser = argparse.ArgumentParser(description="Enhanced Terminal Notepad with Tabs")
    parser.add_argument('files', nargs='*', help='Files to open')
    parser.add_argument('--theme', choices=['default', 'dark', 'light'], 
                       default='default', help='Color theme')
    parser.add_argument('--no-syntax', action='store_true', 
                       help='Disable syntax highlighting')
    args = parser.parse_args()
    
    notepad = TerminalNotepad(args.files)
    
    # Apply command line options
    if args.theme:
        notepad.theme.current_theme = args.theme
    if args.no_syntax:
        notepad.syntax_enabled = False
    
    try:
        curses.wrapper(notepad.run)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()