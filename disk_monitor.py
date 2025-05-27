#!/usr/bin/env python3
"""
Terminal disk usage visualizer with ASCII bars
Usage: python disk_monitor.py [path]
"""

import os
import sys
import shutil
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich import print as rprint
import argparse

def get_disk_usage(path):
    """Get disk usage statistics for a given path"""
    total, used, free = shutil.disk_usage(path)
    return {
        'total': total,
        'used': used,
        'free': free,
        'percent': (used / total) * 100
    }

def format_bytes(bytes_val):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def get_directory_size(path, max_depth=2, current_depth=0):
    """Get directory sizes recursively"""
    if current_depth >= max_depth:
        return 0
    
    total_size = 0
    items = []
    
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path):
                total_size += os.path.getsize(item_path)
            elif os.path.isdir(item_path):
                dir_size = get_directory_size(item_path, max_depth, current_depth + 1)
                total_size += dir_size
                items.append((item, dir_size))
    except (PermissionError, FileNotFoundError):
        pass
    
    return total_size

def create_file_tree(path, max_items=10):
    """Create a visual file tree"""
    tree = Tree(f"📁 {os.path.basename(path) or path}")
    
    try:
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                size = get_directory_size(item_path, max_depth=1)
                items.append((item, size, True))
            else:
                size = os.path.getsize(item_path)
                items.append((item, size, False))
        
        # Sort by size, largest first
        items.sort(key=lambda x: x[1], reverse=True)
        
        for i, (name, size, is_dir) in enumerate(items[:max_items]):
            icon = "📁" if is_dir else "📄"
            size_str = format_bytes(size)
            tree.add(f"{icon} {name} ({size_str})")
            
    except (PermissionError, FileNotFoundError):
        tree.add("❌ Permission denied")
    
    return tree

def main():
    parser = argparse.ArgumentParser(description="Terminal disk usage visualizer")
    parser.add_argument("path", nargs="?", default=".", help="Path to analyze (default: current directory)")
    args = parser.parse_args()
    
    console = Console()
    
    # Get disk usage
    try:
        disk_info = get_disk_usage(args.path)
    except (FileNotFoundError, PermissionError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    
    # Create main display
    console.clear()
    console.print("\n[bold blue]🔍 Terminal Disk Analyzer[/bold blue]\n")
    
    # Disk usage summary
    table = Table(title=f"Disk Usage for: {os.path.abspath(args.path)}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_column("Visual", style="green")
    
    # Create progress bar for disk usage
    used_gb = disk_info['used'] / (1024**3)
    total_gb = disk_info['total'] / (1024**3)
    
    # ASCII progress bar
    bar_width = 30
    filled = int((disk_info['percent'] / 100) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    table.add_row("Total Space", format_bytes(disk_info['total']), "")
    table.add_row("Used Space", format_bytes(disk_info['used']), f"[red]{bar}[/red]")
    table.add_row("Free Space", format_bytes(disk_info['free']), f"{disk_info['percent']:.1f}% used")
    
    console.print(table)
    console.print()
    
    # File tree
    console.print(Panel(create_file_tree(args.path), title="📂 Directory Contents", border_style="blue"))
    
    # Speed test simulation
    console.print("\n[bold green]📊 Performance Metrics[/bold green]")
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        
        # Simulate some metrics
        cpu_task = progress.add_task("CPU Usage", total=100)
        mem_task = progress.add_task("Memory Usage", total=100)
        disk_task = progress.add_task("Disk Usage", total=100)
        
        progress.update(cpu_task, advance=45)  # 45% CPU
        progress.update(mem_task, advance=67)  # 67% Memory
        progress.update(disk_task, advance=disk_info['percent'])
    
    console.print(f"\n[dim]Path analyzed: {os.path.abspath(args.path)}[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
