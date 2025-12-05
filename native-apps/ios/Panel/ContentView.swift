// native-apps/ios/Panel/ContentView.swift

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        if appState.isAuthenticated {
            MainTabView()
        } else {
            LoginView()
        }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "chart.bar.fill")
                }
            
            ServersView()
                .tabItem {
                    Label("Servers", systemImage: "server.rack")
                }
            
            AnalyticsView()
                .tabItem {
                    Label("Analytics", systemImage: "chart.line.uptrend.xyaxis")
                }
            
            PluginsView()
                .tabItem {
                    Label("Plugins", systemImage: "puzzlepiece.extension.fill")
                }
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
        }
    }
}

// MARK: - Placeholder Views

struct ServersView: View {
    var body: some View {
        NavigationView {
            Text("Servers View")
                .navigationTitle("Servers")
        }
    }
}

struct AnalyticsView: View {
    var body: some View {
        NavigationView {
            Text("Analytics View")
                .navigationTitle("Analytics")
        }
    }
}

struct PluginsView: View {
    var body: some View {
        NavigationView {
            Text("Plugins View")
                .navigationTitle("Plugins")
        }
    }
}

struct SettingsView: View {
    var body: some View {
        NavigationView {
            Text("Settings View")
                .navigationTitle("Settings")
        }
    }
}

struct LoginView: View {
    @EnvironmentObject var appState: AppState
    @State private var username = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var showError = false
    @State private var errorMessage = ""
    
    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                // Logo
                Image(systemName: "gamecontroller.fill")
                    .font(.system(size: 80))
                    .foregroundColor(.blue)
                    .padding(.bottom, 40)
                
                // Title
                VStack(spacing: 8) {
                    Text("Welcome to Panel")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    Text("Gaming Platform Management")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                // Login Form
                VStack(spacing: 16) {
                    TextField("Username", text: $username)
                        .textFieldStyle(.roundedBorder)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    
                    SecureField("Password", text: $password)
                        .textFieldStyle(.roundedBorder)
                    
                    Button(action: login) {
                        if isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        } else {
                            Text("Log In")
                                .fontWeight(.semibold)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                    .disabled(isLoading || username.isEmpty || password.isEmpty)
                }
                .padding(.horizontal, 40)
                
                Spacer()
            }
            .padding()
            .alert("Login Failed", isPresented: $showError) {
                Button("OK", role: .cancel) { }
            } message: {
                Text(errorMessage)
            }
        }
    }
    
    private func login() {
        isLoading = true
        
        // Mock login for demonstration
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            isLoading = false
            
            if username == "demo" && password == "demo" {
                appState.isAuthenticated = true
            } else {
                errorMessage = "Invalid username or password"
                showError = true
            }
        }
    }
}

// MARK: - App State

class AppState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var theme: ThemeMode = .system
    
    enum ThemeMode {
        case light, dark, system
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}