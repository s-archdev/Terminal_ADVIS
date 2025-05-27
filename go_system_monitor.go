package main

import (
	"fmt"
	"os"
	"runtime"
	"sort"
	"strings"
	"syscall"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Styles
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#7D56F4")).
			Background(lipgloss.Color("#282828")).
			Padding(0, 1)

	barStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#04B575"))

	usedBarStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF6B6B"))

	infoStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FBBF24")).
			Padding(0, 1)

	headerStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#06D6A0"))
)

// Model represents the state of our application
type model struct {
	width     int
	height    int
	diskInfo  DiskInfo
	sysInfo   SystemInfo
	lastTick  time.Time
	tab       int // Current tab (0: System, 1: Disk, 2: Process)
}

// DiskInfo holds disk usage information
type DiskInfo struct {
	Total uint64
	Used  uint64
	Free  uint64
	Path  string
}

// SystemInfo holds system information
type SystemInfo struct {
	OS           string
	Arch         string
	CPUs         int
	Goroutines   int
	MemTotal     uint64
	MemUsed      uint64
	MemFree      uint64
	LoadAverage  float64
}

// ProcessInfo holds process information
type ProcessInfo struct {
	PID     int
	Name    string
	Memory  uint64
	CPU     float64
}

// Messages for the tea program
type tickMsg time.Time

func tickCmd() tea.Cmd {
	return tea.Tick(time.Second, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

// Initialize the model
func initialModel() model {
	return model{
		lastTick: time.Now(),
		tab:      0,
	}
}

// Init runs any intial IO
func (m model) Init() tea.Cmd {
	return tickCmd()
}

// Update handles messages
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case "tab":
			m.tab = (m.tab + 1) % 3
		case "1":
			m.tab = 0
		case "2":
			m.tab = 1
		case "3":
			m.tab = 2
		}

	case tickMsg:
		m.lastTick = time.Time(msg)
		m.diskInfo = getDiskUsage("/")
		m.sysInfo = getSystemInfo()
		return m, tickCmd()
	}

	return m, nil
}

// View renders the UI
func (m model) View() string {
	if m.width == 0 {
		return "Loading..."
	}

	var content strings.Builder

	// Header
	title := titleStyle.Render("🖥️  Go Terminal System Monitor")
	content.WriteString(title + "\n\n")

	// Tab navigation
	tabs := []string{"System Info", "Disk Usage", "Process Tree"}
	var tabStrings []string
	for i, tab := range tabs {
		if i == m.tab {
			tabStrings = append(tabStrings, headerStyle.Render(fmt.Sprintf("[%d] %s", i+1, tab)))
		} else {
			tabStrings = append(tabStrings, fmt.Sprintf(" %d  %s ", i+1, tab))
		}
	}
	content.WriteString(strings.Join(tabStrings, " | ") + "\n\n")

	// Content based on selected tab
	switch m.tab {
	case 0:
		content.WriteString(m.renderSystemInfo())
	case 1:
		content.WriteString(m.renderDiskInfo())
	case 2:
		content.WriteString(m.renderProcessInfo())
	}

	// Footer
	content.WriteString("\n" + infoStyle.Render("Press 1-3 to switch tabs | Tab to cycle | q to quit"))

	return content.String()
}

// renderSystemInfo displays system information
func (m model) renderSystemInfo() string {
	var content strings.Builder

	content.WriteString(headerStyle.Render("📊 System Information") + "\n\n")

	// System details
	content.WriteString(fmt.Sprintf("OS: %s\n", m.sysInfo.OS))
	content.WriteString(fmt.Sprintf("Architecture: %s\n", m.sysInfo.Arch))
	content.WriteString(fmt.Sprintf("CPU Cores: %d\n", m.sysInfo.CPUs))
	content.WriteString(fmt.Sprintf("Goroutines: %d\n", m.sysInfo.Goroutines))
	content.WriteString(fmt.Sprintf("Last Update: %s\n\n", m.lastTick.Format("15:04:05")))

	// Memory usage
	content.WriteString(headerStyle.Render("💾 Memory Usage") + "\n")
	if m.sysInfo.MemTotal > 0 {
		memPercent := float64(m.sysInfo.MemUsed) / float64(m.sysInfo.MemTotal) * 100
		memBar := createProgressBar(int(memPercent), 40)
		content.WriteString(fmt.Sprintf("Used: %s / %s (%.1f%%)\n",
			formatBytes(m.sysInfo.MemUsed),
			formatBytes(m.sysInfo.MemTotal),
			memPercent))
		content.WriteString(memBar + "\n")
	} else {
		content.WriteString("Memory information not available\n")
	}

	// CPU visualization (simulated)
	content.WriteString("\n" + headerStyle.Render("⚡ CPU Usage") + "\n")
	for i := 0; i < m.sysInfo.CPUs; i++ {
		// Simulate CPU usage (in real implementation, you'd get actual CPU stats)
		usage := (time.Now().Unix() + int64(i)) % 100
		cpuBar := createProgressBar(int(usage), 30)
		content.WriteString(fmt.Sprintf("Core %d: %s %d%%\n", i+1, cpuBar, usage))
	}

	return content.String()
}

// renderDiskInfo displays disk usage information
func (m model) renderDiskInfo() string {
	var content strings.Builder

	content.WriteString(headerStyle.Render("💽 Disk Usage") + "\n\n")

	if m.diskInfo.Total > 0 {
		usedPercent := float64(m.diskInfo.Used) / float64(m.diskInfo.Total) * 100
		freePercent := 100 - usedPercent

		content.WriteString(fmt.Sprintf("Path: %s\n", m.diskInfo.Path))
		content.WriteString(fmt.Sprintf("Total: %s\n", formatBytes(m.diskInfo.Total)))
		content.WriteString(fmt.Sprintf("Used:  %s (%.1f%%)\n", formatBytes(m.diskInfo.Used), usedPercent))
		content.WriteString(fmt.Sprintf("Free:  %s (%.1f%%)\n\n", formatBytes(m.diskInfo.Free), freePercent))

		// Large visual bar
		barWidth := 60
		usedBar := createProgressBar(int(usedPercent), barWidth)
		content.WriteString("Usage Visualization:\n")
		content.WriteString(usedBar + "\n\n")

		// ASCII pie chart representation
		content.WriteString(headerStyle.Render("📈 Usage Breakdown") + "\n")
		content.WriteString(createASCIIPieChart(usedPercent))

		// Disk health simulation
		content.WriteString("\n" + headerStyle.Render("🔍 Disk Health") + "\n")
		content.WriteString(fmt.Sprintf("Status: %s\n", getHealthStatus(usedPercent)))
		content.WriteString(fmt.Sprintf("Read Speed: %s/s (simulated)\n", formatBytes(uint64(150*1024*1024))))
		content.WriteString(fmt.Sprintf("Write Speed: %s/s (simulated)\n", formatBytes(uint64(120*1024*1024))))
	} else {
		content.WriteString("Unable to retrieve disk information\n")
	}

	return content.String()
}

// renderProcessInfo displays a simulated process tree
func (m model) renderProcessInfo() string {
	var content strings.Builder

	content.WriteString(headerStyle.Render("🌳 Process Information") + "\n\n")

	// Simulated process data (in real implementation, you'd read from /proc or use system calls)
	processes := []ProcessInfo{
		{PID: 1, Name: "systemd", Memory: 8 * 1024 * 1024, CPU: 0.1},
		{PID: 123, Name: "go-monitor", Memory: 15 * 1024 * 1024, CPU: 2.5},
		{PID: 456, Name: "ssh", Memory: 4 * 1024 * 1024, CPU: 0.0},
		{PID: 789, Name: "nginx", Memory: 25 * 1024 * 1024, CPU: 1.2},
		{PID: 321, Name: "postgres", Memory: 150 * 1024 * 1024, CPU: 3.8},
	}

	// Sort by memory usage
	sort.Slice(processes, func(i, j int) bool {
		return processes[i].Memory > processes[j].Memory
	})

	content.WriteString(fmt.Sprintf("%-8s %-15s %-12s %-8s %s\n", "PID", "NAME", "MEMORY", "CPU%", "BAR"))
	content.WriteString(strings.Repeat("─", 60) + "\n")

	maxMem := processes[0].Memory
	for _, proc := range processes {
		memPercent := float64(proc.Memory) / float64(maxMem) * 100
		memBar := createProgressBar(int(memPercent), 15)
		content.WriteString(fmt.Sprintf("%-8d %-15s %-12s %-8.1f %s\n",
			proc.PID,
			proc.Name,
			formatBytes(proc.Memory),
			proc.CPU,
			memBar))
	}

	content.WriteString("\n" + infoStyle.Render("Simulated data - Real implementation would read from system"))
	return content.String()
}

// Helper functions

func createProgressBar(percent, width int) string {
	if percent > 100 {
		percent = 100
	}
	if percent < 0 {
		percent = 0
	}

	filled := int(float64(width) * float64(percent) / 100.0)
	bar := strings.Repeat("█", filled) + strings.Repeat("░", width-filled)

	var style lipgloss.Style
	if percent > 80 {
		style = usedBarStyle // Red for high usage
	} else {
		style = barStyle // Green for normal usage
	}

	return style.Render(bar)
}

func createASCIIPieChart(usedPercent float64) string {
	var chart strings.Builder
	
	// Simple text-based pie representation
	used := int(usedPercent / 10)
	free := 10 - used
	
	chart.WriteString("┌" + strings.Repeat("─", 12) + "┐\n")
	chart.WriteString("│ USED: ")
	chart.WriteString(usedBarStyle.Render(strings.Repeat("█", used)))
	chart.WriteString(strings.Repeat(" ", free))
	chart.WriteString(" │\n")
	chart.WriteString("│ FREE: ")
	chart.WriteString(barStyle.Render(strings.Repeat("█", free)))
	chart.WriteString(strings.Repeat(" ", used))
	chart.WriteString(" │\n")
	chart.WriteString("└" + strings.Repeat("─", 12) + "┘\n")
	
	return chart.String()
}

func getHealthStatus(usedPercent float64) string {
	switch {
	case usedPercent < 70:
		return barStyle.Render("✅ Healthy")
	case usedPercent < 85:
		return infoStyle.Render("⚠️  Warning")
	default:
		return usedBarStyle.Render("🚨 Critical")
	}
}

func formatBytes(bytes uint64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := uint64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

// System information gathering functions

func getDiskUsage(path string) DiskInfo {
	var stat syscall.Statfs_t
	err := syscall.Statfs(path, &stat)
	if err != nil {
		return DiskInfo{Path: path}
	}

	total := stat.Blocks * uint64(stat.Bsize)
	free := stat.Bavail * uint64(stat.Bsize)
	used := total - free

	return DiskInfo{
		Total: total,
		Used:  used,
		Free:  free,
		Path:  path,
	}
}

func getSystemInfo() SystemInfo {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	return SystemInfo{
		OS:         runtime.GOOS,
		Arch:       runtime.GOARCH,
		CPUs:       runtime.NumCPU(),
		Goroutines: runtime.NumGoroutine(),
		MemTotal:   m.Sys,
		MemUsed:    m.Alloc,
		MemFree:    m.Sys - m.Alloc,
	}
}

func main() {
	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Error: %v", err)
		os.Exit(1)
	}
}
