// native-apps/ios/Panel/ViewControllers/DashboardView.swift

import SwiftUI
import Charts

struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()
    @State private var isRefreshing = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Header Gradient
                    ZStack(alignment: .bottom) {
                        LinearGradient(
                            colors: [Color("PrimaryColor"), Color("SecondaryColor")],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        .frame(height: 150)
                        .ignoresSafeArea(edges: .top)
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Dashboard")
                                .font(.largeTitle)
                                .fontWeight(.bold)
                                .foregroundColor(.white)
                            Text("Panel Gaming Platform")
                                .font(.subheadline)
                                .foregroundColor(.white.opacity(0.8))
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal)
                        .padding(.bottom, 16)
                    }
                    
                    VStack(spacing: 16) {
                        // Stats Grid
                        if let stats = viewModel.dashboardStats {
                            StatsGridView(stats: stats)
                        }
                        
                        // Performance Chart
                        if !viewModel.performanceData.isEmpty {
                            PerformanceChartView(data: viewModel.performanceData)
                        }
                        
                        // Recent Alerts
                        if !viewModel.alerts.isEmpty {
                            AlertsSectionView(alerts: viewModel.alerts)
                        }
                        
                        // Quick Actions
                        QuickActionsView()
                    }
                    .padding(.horizontal)
                }
            }
            .refreshable {
                await viewModel.refresh()
            }
            .navigationBarHidden(true)
        }
        .task {
            await viewModel.loadDashboard()
        }
    }
}

struct StatsGridView: View {
    let stats: DashboardStats
    
    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 12) {
                StatCard(
                    icon: "server.rack",
                    label: "Total Servers",
                    value: "\(stats.totalServers)",
                    color: .green
                )
                StatCard(
                    icon: "play.circle.fill",
                    label: "Active Servers",
                    value: "\(stats.activeServers)",
                    color: .blue
                )
            }
            
            HStack(spacing: 12) {
                StatCard(
                    icon: "person.3.fill",
                    label: "Total Players",
                    value: "\(stats.totalPlayers)",
                    color: .orange
                )
                StatCard(
                    icon: "cpu",
                    label: "Avg CPU",
                    value: String(format: "%.1f%%", stats.avgCpuUsage),
                    color: .purple
                )
            }
        }
    }
}

struct StatCard: View {
    let icon: String
    let label: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                ZStack {
                    Circle()
                        .fill(color.opacity(0.2))
                        .frame(width: 56, height: 56)
                    Image(systemName: icon)
                        .font(.system(size: 24))
                        .foregroundColor(color)
                }
                
                Spacer()
                
                Text(value)
                    .font(.title2)
                    .fontWeight(.bold)
            }
            
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
}

struct PerformanceChartView: View {
    let data: [PerformanceDataPoint]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Performance Over Time")
                .font(.headline)
            
            if #available(iOS 16.0, *) {
                Chart {
                    ForEach(data) { point in
                        LineMark(
                            x: .value("Time", point.timestamp),
                            y: .value("CPU", point.cpuUsage)
                        )
                        .foregroundStyle(.red)
                        
                        LineMark(
                            x: .value("Time", point.timestamp),
                            y: .value("Memory", point.memoryUsage)
                        )
                        .foregroundStyle(.blue)
                    }
                }
                .frame(height: 200)
                .chartLegend(position: .bottom)
            } else {
                // Fallback for iOS 15
                Text("Chart: CPU/Memory over 24h")
                    .frame(height: 200)
                    .frame(maxWidth: .infinity)
                    .background(Color(.systemGray6))
                    .cornerRadius(8)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
}

struct AlertsSectionView: View {
    let alerts: [ServerAlert]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent Alerts")
                .font(.headline)
            
            ForEach(alerts.prefix(3)) { alert in
                AlertCardView(alert: alert)
            }
            
            if alerts.count > 3 {
                Button(action: {
                    // Navigate to all alerts
                }) {
                    HStack {
                        Text("View All Alerts (\(alerts.count))")
                        Image(systemName: "chevron.right")
                    }
                    .font(.subheadline)
                    .foregroundColor(.blue)
                }
                .frame(maxWidth: .infinity)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
}

struct AlertCardView: View {
    let alert: ServerAlert
    
    var alertColor: Color {
        switch alert.severity {
        case "critical": return .red
        case "warning": return .orange
        case "info": return .blue
        default: return .gray
        }
    }
    
    var body: some View {
        HStack(spacing: 12) {
            Rectangle()
                .fill(alertColor)
                .frame(width: 4)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(alert.title)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text(alert.message)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(alert.timestamp.formatted(date: .omitted, time: .shortened))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
        .padding(12)
        .background(Color(.systemGray6))
        .cornerRadius(8)
    }
}

struct QuickActionsView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Quick Actions")
                .font(.headline)
            
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                QuickActionButton(
                    icon: "plus.circle.fill",
                    label: "New Server",
                    color: .green
                ) {
                    // Navigate to create server
                }
                
                QuickActionButton(
                    icon: "chart.line.uptrend.xyaxis",
                    label: "Analytics",
                    color: .blue
                ) {
                    // Navigate to analytics
                }
                
                QuickActionButton(
                    icon: "puzzlepiece.extension.fill",
                    label: "Plugins",
                    color: .orange
                ) {
                    // Navigate to plugins
                }
                
                QuickActionButton(
                    icon: "gearshape.fill",
                    label: "Settings",
                    color: .purple
                ) {
                    // Navigate to settings
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(16)
        .shadow(color: .black.opacity(0.1), radius: 4, x: 0, y: 2)
    }
}

struct QuickActionButton: View {
    let icon: String
    let label: String
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 32))
                    .foregroundColor(color)
                
                Text(label)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(.primary)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 100)
            .background(Color(.systemGray6))
            .cornerRadius(12)
        }
    }
}

// MARK: - View Model

@MainActor
class DashboardViewModel: ObservableObject {
    @Published var dashboardStats: DashboardStats?
    @Published var performanceData: [PerformanceDataPoint] = []
    @Published var alerts: [ServerAlert] = []
    @Published var isLoading = false
    @Published var error: Error?
    
    func loadDashboard() async {
        isLoading = true
        defer { isLoading = false }
        
        do {
            async let statsTask = APIService.shared.getAnalytics()
            async let serversTask = APIService.shared.getServers()
            
            let (analytics, servers) = try await (statsTask, serversTask)
            
            // Process data
            self.dashboardStats = DashboardStats(
                totalServers: servers.count,
                activeServers: servers.filter { $0.status == "running" }.count,
                totalPlayers: servers.reduce(0) { $0 + $1.playerCount },
                avgCpuUsage: analytics.avgCpuUsage ?? 0,
                avgMemoryUsage: analytics.avgMemoryUsage ?? 0
            )
            
            self.performanceData = analytics.performanceHistory ?? []
            self.alerts = analytics.alerts ?? []
            
        } catch {
            self.error = error
            print("Failed to load dashboard: \(error)")
        }
    }
    
    func refresh() async {
        await loadDashboard()
    }
}

#Preview {
    DashboardView()
}