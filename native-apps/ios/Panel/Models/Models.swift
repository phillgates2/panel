// native-apps/ios/Panel/Models/Models.swift

import Foundation

// MARK: - Server Models

struct Server: Identifiable, Codable {
    let id: String
    let name: String
    let gameType: String
    let status: String
    let playerCount: Int
    let maxPlayers: Int
    let cpuUsage: Float
    let memoryUsage: Float
    let ipAddress: String
    let region: String?
    let createdAt: Date?
    
    enum CodingKeys: String, CodingKey {
        case id, name, status, region
        case gameType = "game_type"
        case playerCount = "player_count"
        case maxPlayers = "max_players"
        case cpuUsage = "cpu_usage"
        case memoryUsage = "memory_usage"
        case ipAddress = "ip_address"
        case createdAt = "created_at"
    }
}

// MARK: - Dashboard Models

struct DashboardStats: Codable {
    let totalServers: Int
    let activeServers: Int
    let totalPlayers: Int
    let avgCpuUsage: Float
    let avgMemoryUsage: Float
    
    enum CodingKeys: String, CodingKey {
        case totalServers = "total_servers"
        case activeServers = "active_servers"
        case totalPlayers = "total_players"
        case avgCpuUsage = "avg_cpu_usage"
        case avgMemoryUsage = "avg_memory_usage"
    }
}

struct ServerAlert: Identifiable, Codable {
    let id: String
    let title: String
    let message: String
    let severity: String
    let timestamp: Date
    let serverId: String?
    
    enum CodingKeys: String, CodingKey {
        case id, title, message, severity, timestamp
        case serverId = "server_id"
    }
}

struct PerformanceDataPoint: Identifiable, Codable {
    let id: UUID
    let timestamp: Date
    let cpuUsage: Float
    let memoryUsage: Float
    
    enum CodingKeys: String, CodingKey {
        case timestamp
        case cpuUsage = "cpu_usage"
        case memoryUsage = "memory_usage"
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = UUID()
        self.timestamp = try container.decode(Date.self, forKey: .timestamp)
        self.cpuUsage = try container.decode(Float.self, forKey: .cpuUsage)
        self.memoryUsage = try container.decode(Float.self, forKey: .memoryUsage)
    }
}

// MARK: - Analytics Models

struct AnalyticsData: Codable {
    let avgCpuUsage: Float?
    let avgMemoryUsage: Float?
    let performanceHistory: [PerformanceDataPoint]?
    let alerts: [ServerAlert]?
    
    enum CodingKeys: String, CodingKey {
        case avgCpuUsage = "avg_cpu_usage"
        case avgMemoryUsage = "avg_memory_usage"
        case performanceHistory = "performance_history"
        case alerts
    }
}

// MARK: - Authentication Models

struct AuthResponse: Codable {
    let token: String
    let refreshToken: String?
    let expiresAt: Date?
    let user: UserProfile?
    
    enum CodingKeys: String, CodingKey {
        case token
        case refreshToken = "refresh_token"
        case expiresAt = "expires_at"
        case user
    }
}

struct RegisterRequest: Codable {
    let username: String
    let email: String
    let password: String
}

struct UserProfile: Codable {
    let id: String
    let username: String
    let email: String
    let displayName: String?
    let avatarUrl: String?
    
    enum CodingKeys: String, CodingKey {
        case id, username, email
        case displayName = "display_name"
        case avatarUrl = "avatar_url"
    }
}

// MARK: - Server Management Models

struct ServerConfig: Codable {
    let name: String
    let gameType: String
    let maxPlayers: Int
    let region: String
    
    enum CodingKeys: String, CodingKey {
        case name, region
        case gameType = "game_type"
        case maxPlayers = "max_players"
    }
}

struct ServerUpdate: Codable {
    let name: String?
    let maxPlayers: Int?
    
    enum CodingKeys: String, CodingKey {
        case name
        case maxPlayers = "max_players"
    }
}

struct ServerAction: Codable {
    let success: Bool
    let message: String
}

struct ServerDetails: Codable {
    let server: Server
    let metrics: ServerMetrics
    let players: [Player]
}

struct ServerMetrics: Codable {
    let cpuHistory: [Float]
    let memoryHistory: [Float]
    let networkIn: Float
    let networkOut: Float
    
    enum CodingKeys: String, CodingKey {
        case cpuHistory = "cpu_history"
        case memoryHistory = "memory_history"
        case networkIn = "network_in"
        case networkOut = "network_out"
    }
}

struct Player: Identifiable, Codable {
    let id: String
    let username: String
    let joinedAt: Date
    let playtime: Int
    
    enum CodingKeys: String, CodingKey {
        case id, username, playtime
        case joinedAt = "joined_at"
    }
}

// MARK: - Plugin Models

struct Plugin: Identifiable, Codable {
    let id: String
    let name: String
    let description: String
    let version: String
    let author: String
    let rating: Float
    let downloads: Int
    let price: Float
    let imageUrl: String?
    
    enum CodingKeys: String, CodingKey {
        case id, name, description, version, author, rating, downloads, price
        case imageUrl = "image_url"
    }
}

struct PluginDetails: Codable {
    let plugin: Plugin
    let readme: String
    let changelog: String
    let screenshots: [String]
}

struct PluginAction: Codable {
    let success: Bool
    let message: String
}

// MARK: - Notification Models

struct PanelNotification: Identifiable, Codable {
    let id: String
    let title: String
    let body: String
    let type: String
    let read: Bool
    let createdAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, title, body, type, read
        case createdAt = "created_at"
    }
}

// MARK: - Blockchain Models

struct WalletBalance: Codable {
    let balance: Double
    let currency: String
}

struct NFTAsset: Identifiable, Codable {
    let id: String
    let name: String
    let description: String
    let imageUrl: String
    let owner: String
    let attributes: [String: String]
    
    enum CodingKeys: String, CodingKey {
        case id, name, description, owner, attributes
        case imageUrl = "image_url"
    }
}

// MARK: - Support Models

struct SupportTicketRequest: Codable {
    let subject: String
    let description: String
    let priority: String
}

struct SupportTicket: Identifiable, Codable {
    let id: String
    let subject: String
    let description: String
    let status: String
    let priority: String
    let createdAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, subject, description, status, priority
        case createdAt = "created_at"
    }
}

struct KBArticle: Identifiable, Codable {
    let id: String
    let title: String
    let content: String
    let category: String
    let tags: [String]
}

// MARK: - Profile Models

struct ProfileUpdate: Codable {
    let displayName: String?
    let email: String?
    
    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case email
    }
}

struct PlayerAnalytics: Codable {
    let totalPlayers: Int
    let activePlayers: Int
    let newPlayers: Int
    let retentionRate: Float
    
    enum CodingKeys: String, CodingKey {
        case totalPlayers = "total_players"
        case activePlayers = "active_players"
        case newPlayers = "new_players"
        case retentionRate = "retention_rate"
    }
}