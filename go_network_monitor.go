package main

import (
	"bufio"
	"fmt"
	"math"
	"math/rand"
	"os"
	"strconv"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Styles
var (
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#00D4AA")).
			Background(lipgloss.Color("#1a1a1a")).
			Padding(0, 2)

	downloadStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#00FF87")).
			Bold(true)

	uploadStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF6B9D")).
			Bold(true)

	infoStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#87CEEB")).
			Italic(true)

	alertStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF4444")).
			Bold(true)

	headerStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#FFD700")).
			Underline(true)

	borderStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#444444")).
			Padding(1, 2)
)

// NetworkInterface represents a network interface
type NetworkInterface struct {
	Name         string
	BytesRecv    uint64
	BytesSent    uint64
	PacketsRecv  uint64
	PacketsSent  uint64
	LastRecv     uint64
	LastSent     uint64
	DownloadRate float64 // bytes per second
	UploadRate   float64 // bytes per second
	History      []SpeedPoint
}

// SpeedPoint represents a point in time for speed history
type SpeedPoint struct {
	Download float64
	Upload   float64
	Time     time.Time
}

// ConnectionInfo represents network connection information
type ConnectionInfo struct {
	LocalAddr  string
	RemoteAddr string
	State      string
	Protocol   string
}

// Model represents the application state
type model struct {
	interfaces    map[string]*NetworkInterface
	connections   []ConnectionInfo
	width         int
	height        int
	currentTab    int // 0: Speed, 1: Interfaces, 2: Connections, 3: Graph
	lastUpdate    time.Time
	maxDownload   float64
	maxUpload     float64
	totalDownload uint64
	totalUpload   uint64
	isRunning     bool
}

// Messages
type tickMsg time.Time
type speedTestMsg struct {
	download float64
	upload   float64
}

func tickCmd() tea.Cmd {
	return tea.Tick(time.Millisecond*500, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func speedTestCmd() tea.Cmd {
	return func() tea.Msg {
		// Simulate network activity with some randomness
		baseDown := 50 + rand.Float64()*100  // 50-150 Mbps base
		baseUp := 20 + rand.Float64()*40     // 20-60 Mbps base
		
		// Add some spikes and variations
		variation := 0.3 + 0.4*math.Sin(float64(time.Now().Unix())/10.0)
		download := baseDown * (0.7 + variation*0.6)
		upload := baseUp * (0.8 + variation*0.4)
		
		return speedTestMsg{
			download: download * 1024 * 1024 / 8, // Convert Mbps to bytes/sec
			upload:   upload * 1024 * 1024 / 8,
		}
	}
}

func initialModel() model {
	interfaces := make(map[string]*NetworkInterface)
	
	// Initialize with common interface names
	commonInterfaces := []string{"eth0", "wlan0", "lo", "docker0"}
	for _, name := range commonInterfaces {
		interfaces[name] = &NetworkInterface{
			Name:    name,
			History: make([]SpeedPoint, 0, 60), // Keep 30 seconds of history
		}
	}

	return model{
		interfaces:  interfaces,
		connections: generateMockConnections(),
		currentTab:  0,
		lastUpdate:  time.Now(),
		isRunning:   true,
	}
}

func (m model) Init() tea.Cmd {
	return tea.Batch(tickCmd(), speedTestCmd())
}

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
			m.currentTab = (m.currentTab + 1) % 4
		case "1":
			m.currentTab = 0
		case "2":
			m.currentTab = 1
		case "3":
			m.currentTab = 2
		case "4":
			m.currentTab = 3
		case "r":
			// Reset statistics
			for _, iface := range m.interfaces {
				iface.History = make([]SpeedPoint, 0, 60)
			}
			m.maxDownload = 0
			m.maxUpload = 0
			m.totalDownload = 0
			m.totalUpload = 0
		case "s":
			// Toggle running state
			m.isRunning = !m.isRunning
		}

	case tickMsg:
		m.lastUpdate = time.Time(msg)
		if m.isRunning {
			m.updateNetworkStats()
			return m, tea.Batch(tickCmd(), speedTestCmd())
		}
		return m, tickCmd()

	case speedTestMsg:
		if m.isRunning {
			// Update main interface (eth0) with speed test data
			if eth0, exists := m.interfaces["eth0"]; exists {
				eth0.DownloadRate = msg.download
				eth0.UploadRate = msg.upload
				
				// Update maximums
				if msg.download > m.maxDownload {
					m.maxDownload = msg.download
				}
				if msg.upload > m.maxUpload {
					m.maxUpload = msg.upload
				}
				
				// Add to history
				point := SpeedPoint{
					Download: msg.download,
					Upload:   msg.upload,
					Time:     time.Now(),
				}
				eth0.History = append(eth0.History, point)
				
				// Keep only last 60 points (30 seconds)
				if len(eth0.History) > 60 {
					eth0.History = eth0.History[1:]
				}
				
				// Update totals (simulate)
				m.totalDownload += uint64(msg.download / 2) // Rough approximation
				m.totalUpload += uint64(msg.upload / 2)
			}
		}
	}

	return m, nil
}

func (m model) View() string {
	if m.width == 0 {
		return "Initializing network monitor..."
	}

	var content strings.Builder

	// Header
	status := "🟢 RUNNING"
	if !m.isRunning {
		status = "🔴 PAUSED"
	}
	
	header := titleStyle.Render("🌐 Network Speed Visualizer") + " " + status
	content.WriteString(header + "\n\n")

	// Tab navigation
	tabs := []string{"📊 Live Speed", "🔌 Interfaces", "🔗 Connections", "📈 Graph"}
	var tabStrings []string
	for i, tab := range tabs {
		if i == m.currentTab {
			tabStrings = append(tabStrings, headerStyle.Render(fmt.Sprintf("[%d] %s", i+1, tab)))
		} else {
			tabStrings = append(tabStrings, fmt.Sprintf(" %d  %s ", i+1, tab))
		}
	}
	content.WriteString(strings.Join(tabStrings, " | ") + "\n\n")

	// Content based on current tab
	switch m.currentTab {
	case 0:
		content.WriteString(m.renderSpeedView())
	case 1:
		content.WriteString(m.renderInterfacesView())
	case 2:
		content.WriteString(m.renderConnectionsView())
	case 3:
		content.WriteString(m.renderGraphView())
	}

	// Footer
	footer := "\n" + infoStyle.Render("Controls: [1-4] Switch tabs | [Tab] Cycle | [R] Reset | [S] Start/Stop | [Q] Quit")
	content.WriteString(footer)

	return content.String()
}

func (m model) renderSpeedView() string {
	var content strings.Builder

	eth0 := m.interfaces["eth0"]
	if eth0 == nil {
		return "No network interface data available"
	}

	// Current speeds
	content.WriteString(headerStyle.Render("⚡ Current Network Speed") + "\n\n")
	
	downloadMbps := eth0.DownloadRate * 8 / (1024 * 1024) // Convert to Mbps
	uploadMbps := eth0.UploadRate * 8 / (1024 * 1024)
	
	// Large speed display
	content.WriteString(fmt.Sprintf("📥 Download: %s %.2f Mbps\n", 
		downloadStyle.Render("▼"), downloadMbps))
	content.WriteString(fmt.Sprintf("📤 Upload:   %s %.2f Mbps\n\n", 
		uploadStyle.Render("▲"), uploadMbps))

	// Visual bars
	maxBarWidth := 50
	if m.width > 80 {
		maxBarWidth = m.width - 30
	}

	// Download bar
	maxSpeed := math.Max(m.maxDownload, eth0.DownloadRate*1.2)
	if maxSpeed == 0 {
		maxSpeed = 1
	}
	downloadPercent := int((eth0.DownloadRate / maxSpeed) * 100)
	downloadBar := createAnimatedBar(downloadPercent, maxBarWidth, "download")
	content.WriteString(fmt.Sprintf("Download: %s %s/s\n", downloadBar, formatBytes(uint64(eth0.DownloadRate))))

	// Upload bar
	maxUpSpeed := math.Max(m.maxUpload, eth0.UploadRate*1.2)
	if maxUpSpeed == 0 {
		maxUpSpeed = 1
	}
	uploadPercent := int((eth0.UploadRate / maxUpSpeed) * 100)
	uploadBar := createAnimatedBar(uploadPercent, maxBarWidth, "upload")
	content.WriteString(fmt.Sprintf("Upload:   %s %s/s\n\n", uploadBar, formatBytes(uint64(eth0.UploadRate))))

	// Statistics
	content.WriteString(headerStyle.Render("📊 Session Statistics") + "\n")
	content.WriteString(fmt.Sprintf("Total Downloaded: %s\n", formatBytes(m.totalDownload)))
	content.WriteString(fmt.Sprintf("Total Uploaded:   %s\n", formatBytes(m.totalUpload)))
	content.WriteString(fmt.Sprintf("Peak Download:    %.2f Mbps\n", m.maxDownload*8/(1024*1024)))
	content.WriteString(fmt.Sprintf("Peak Upload:      %.2f Mbps\n", m.maxUpload*8/(1024*1024)))
	content.WriteString(fmt.Sprintf("Duration:         %v\n", time.Since(m.lastUpdate).Truncate(time.Second)))

	return content.String()
}

func (m model) renderInterfacesView() string {
	var content strings.Builder

	content.WriteString(headerStyle.Render("🔌 Network Interfaces") + "\n\n")

	content.WriteString(fmt.Sprintf("%-12s %-15s %-15s %-10s %-10s\n", 
		"INTERFACE", "DOWNLOAD", "UPLOAD", "PACKETS RX", "PACKETS TX"))
	content.WriteString(strings.Repeat("─", 70) + "\n")

	for name, iface := range m.interfaces {
		downloadRate := formatBytes(uint64(iface.DownloadRate)) + "/s"
		uploadRate := formatBytes(uint64(iface.UploadRate)) + "/s"
		
		// Simulate some packet data
		packetsRx := fmt.Sprintf("%dk", rand.Intn(1000)+100)
		packetsTx := fmt.Sprintf("%dk", rand.Intn(500)+50)
		
		content.WriteString(fmt.Sprintf("%-12s %-15s %-15s %-10s %-10s\n",
			name, downloadRate, uploadRate, packetsRx, packetsTx))
	}

	content.WriteString("\n" + infoStyle.Render("Real implementation would read from /proc/net/dev or /sys/class/net/"))

	return content.String()
}

func (m model) renderConnectionsView() string {
	var content strings.Builder

	content.WriteString(headerStyle.Render("🔗 Active Connections") + "\n\n")

	content.WriteString(fmt.Sprintf("%-8s %-25s %-25s %-12s\n", 
		"PROTO", "LOCAL ADDRESS", "REMOTE ADDRESS", "STATE"))
	content.WriteString(strings.Repeat("─", 75) + "\n")

	for _, conn := range m.connections {
		stateStyle := infoStyle
		if conn.State == "ESTABLISHED" {
			stateStyle = downloadStyle
		} else if conn.State == "LISTEN" {
			stateStyle = uploadStyle
		}

		content.WriteString(fmt.Sprintf("%-8s %-25s %-25s %s\n",
			conn.Protocol,
			conn.LocalAddr,
			conn.RemoteAddr,
			stateStyle.Render(conn.State)))
	}

	content.WriteString("\n" + infoStyle.Render("Simulated connections - Real implementation would read from /proc/net/tcp"))

	return content.String()
}

func (m model) renderGraphView() string {
	var content strings.Builder

	content.WriteString(headerStyle.Render("📈 Speed History Graph") + "\n\n")

	eth0 := m.interfaces["eth0"]
	if eth0 == nil || len(eth0.History) == 0 {
		content.WriteString("No history data available yet...\n")
		return content.String()
	}

	// ASCII graph
	graphHeight := 10
	graphWidth := 60
	if m.width > 80 {
		graphWidth = m.width - 20
	}

	// Find max values for scaling
	maxVal := 0.0
	for _, point := range eth0.History {
		if point.Download > maxVal {
			maxVal = point.Download
		}
		if point.Upload > maxVal {
			maxVal = point.Upload
		}
	}

	if maxVal == 0 {
		maxVal = 1
	}

	// Draw graph
	content.WriteString("Speed over time (last 30 seconds):\n\n")
	
	for row := graphHeight - 1; row >= 0; row-- {
		threshold := maxVal * float64(row) / float64(graphHeight-1)
		
		// Y-axis label
		content.WriteString(fmt.Sprintf("%6s │", formatBytes(uint64(threshold))+"/s"))
		
		// Graph line
		historyLen := len(eth0.History)
		step := float64(historyLen) / float64(graphWidth)
		
		for col := 0; col < graphWidth; col++ {
			idx := int(float64(col) * step)
			if idx >= historyLen {
				idx = historyLen - 1
			}
			
			point := eth0.History[idx]
			char := " "
			
			if point.Download >= threshold {
				char = downloadStyle.Render("▓")
			} else if point.Upload >= threshold {
				char = uploadStyle.Render("░")
			}
			
			content.WriteString(char)
		}
		content.WriteString("\n")
	}
	
	// X-axis
	content.WriteString("       └" + strings.Repeat("─", graphWidth) + "\n")
	content.WriteString("        " + strings.Repeat(" ", graphWidth-15) + "Time →\n\n")
	
	// Legend
	content.WriteString("Legend: " + downloadStyle.Render("▓ Download") + " " + uploadStyle.Render("░ Upload") + "\n")

	return content.String()
}

// Helper functions

func createAnimatedBar(percent, width int, barType string) string {
	if percent > 100 {
		percent = 100
	}
	if percent < 0 {
		percent = 0
	}

	filled := int(float64(width) * float64(percent) / 100.0)
	
	var bar strings.Builder
	var style lipgloss.Style
	
	if barType == "download" {
		style = downloadStyle
	} else {
		style = uploadStyle
	}
	
	// Create animated effect with different characters
	animChars := []string{"█", "▉", "▊", "▋", "▌", "▍", "▎", "▏"}
	animFrame := int(time.Now().UnixMilli()/200) % len(animChars)
	
	for i := 0; i < width; i++ {
		if i < filled-1 {
			bar.WriteString("█")
		} else if i == filled-1 && filled > 0 {
			bar.WriteString(animChars[animFrame])
		} else {
			bar.WriteString("░")
		}
	}
	
	return style.Render(bar.String())
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

func (m *model) updateNetworkStats() {
	// In a real implementation, you would read from /proc/net/dev
	// This simulates reading network interface statistics
	
	// Update other interfaces with some simulated data
	for name, iface := range m.interfaces {
		if name != "eth0" { // eth0 is updated by speed test
			// Simulate some activity
			iface.DownloadRate = rand.Float64() * 1024 * 1024 // 0-1 MB/s
			iface.UploadRate = rand.Float64() * 512 * 1024    // 0-512 KB/s
		}
	}
}

func generateMockConnections() []ConnectionInfo {
	connections := []ConnectionInfo{
		{"127.0.0.1:8080", "127.0.0.1:54321", "ESTABLISHED", "TCP"},
		{"0.0.0.0:22", "*:*", "LISTEN", "TCP"},
		{"192.168.1.100:443", "8.8.8.8:53", "ESTABLISHED", "TCP"},
		{"0.0.0.0:80", "*:*", "LISTEN", "TCP"},
		{"192.168.1.100:12345", "140.82.112.3:443", "ESTABLISHED", "TCP"},
		{"127.0.0.1:5432", "127.0.0.1:54890", "ESTABLISHED", "TCP"},
		{"0.0.0.0:3000", "*:*", "LISTEN", "TCP"},
		{"192.168.1.100:56789", "151.101.1.140:443", "TIME_WAIT", "TCP"},
	}
	return connections
}

func readNetworkInterfaces() map[string]*NetworkInterface {
	interfaces := make(map[string]*NetworkInterface)
	
	// Try to read from /proc/net/dev (Linux)
	file, err := os.Open("/proc/net/dev")
	if err != nil {
		// Fallback to mock data if /proc is not available
		return interfaces
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	// Skip header lines
	scanner.Scan()
	scanner.Scan()

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		fields := strings.Fields(line)
		
		if len(fields) >= 10 {
			name := strings.TrimSuffix(fields[0], ":")
			
			bytesRecv, _ := strconv.ParseUint(fields[1], 10, 64)
			packetsRecv, _ := strconv.ParseUint(fields[2], 10, 64)
			bytesSent, _ := strconv.ParseUint(fields[9], 10, 64)
			packetsSent, _ := strconv.ParseUint(fields[10], 10, 64)
			
			interfaces[name] = &NetworkInterface{
				Name:        name,
				BytesRecv:   bytesRecv,
				BytesSent:   bytesSent,
				PacketsRecv: packetsRecv,
				PacketsSent: packetsSent,
				History:     make([]SpeedPoint, 0, 60),
			}
		}
	}

	return interfaces
}

func main() {
	rand.Seed(time.Now().UnixNano())
	
	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Error running network monitor: %v", err)
		os.Exit(1)
	}
}
