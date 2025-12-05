// native-apps/ios/Panel/Services/APIService.swift

import Foundation
import Combine

enum APIError: Error {
    case invalidURL
    case invalidResponse
    case unauthorized
    case serverError(String)
    case networkError(Error)
}

class APIService: ObservableObject {
    static let shared = APIService()
    
    private let baseURL: String
    private let session: URLSession
    private var cancellables = Set<AnyCancellable>()
    
    @Published var isAuthenticated = false
    
    private init() {
        #if DEBUG
        self.baseURL = "http://localhost:5000"
        #else
        self.baseURL = "https://api.panel.dev"
        #endif
        
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: configuration)
        
        // Check authentication status
        if let token = KeychainService.shared.getToken() {
            isAuthenticated = !token.isEmpty
        }
    }
    
    // MARK: - Authentication
    
    func login(username: String, password: String) -> AnyPublisher<AuthResponse, APIError> {
        let endpoint = "/api/auth/login"
        let body = ["username": username, "password": password]
        
        return request(endpoint: endpoint, method: "POST", body: body)
            .handleEvents(receiveOutput: { [weak self] (response: AuthResponse) in
                KeychainService.shared.saveToken(response.token)
                self?.isAuthenticated = true
            })
            .eraseToAnyPublisher()
    }
    
    func logout() -> AnyPublisher<Void, APIError> {
        let endpoint = "/api/auth/logout"
        
        return request(endpoint: endpoint, method: "POST", body: nil as String?)
            .handleEvents(receiveOutput: { [weak self] _ in
                KeychainService.shared.deleteToken()
                self?.isAuthenticated = false
            })
            .eraseToAnyPublisher()
    }
    
    func register(userData: RegisterRequest) -> AnyPublisher<AuthResponse, APIError> {
        let endpoint = "/api/auth/register"
        return request(endpoint: endpoint, method: "POST", body: userData)
    }
    
    // MARK: - Server Management
    
    func getServers() -> AnyPublisher<[Server], APIError> {
        let endpoint = "/api/servers"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func getServerDetails(serverId: String) -> AnyPublisher<ServerDetails, APIError> {
        let endpoint = "/api/servers/\(serverId)"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func createServer(config: ServerConfig) -> AnyPublisher<Server, APIError> {
        let endpoint = "/api/servers"
        return request(endpoint: endpoint, method: "POST", body: config)
    }
    
    func updateServer(serverId: String, updates: ServerUpdate) -> AnyPublisher<Server, APIError> {
        let endpoint = "/api/servers/\(serverId)"
        return request(endpoint: endpoint, method: "PUT", body: updates)
    }
    
    func deleteServer(serverId: String) -> AnyPublisher<Void, APIError> {
        let endpoint = "/api/servers/\(serverId)"
        return request(endpoint: endpoint, method: "DELETE", body: nil as String?)
    }
    
    func startServer(serverId: String) -> AnyPublisher<ServerAction, APIError> {
        let endpoint = "/api/servers/\(serverId)/start"
        return request(endpoint: endpoint, method: "POST", body: nil as String?)
    }
    
    func stopServer(serverId: String) -> AnyPublisher<ServerAction, APIError> {
        let endpoint = "/api/servers/\(serverId)/stop"
        return request(endpoint: endpoint, method: "POST", body: nil as String?)
    }
    
    func restartServer(serverId: String) -> AnyPublisher<ServerAction, APIError> {
        let endpoint = "/api/servers/\(serverId)/restart"
        return request(endpoint: endpoint, method: "POST", body: nil as String?)
    }
    
    // MARK: - Analytics
    
    func getAnalytics(timeRange: String = "24h") -> AnyPublisher<AnalyticsData, APIError> {
        let endpoint = "/api/analytics/dashboard?timeRange=\(timeRange)"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func getServerMetrics(serverId: String) -> AnyPublisher<ServerMetrics, APIError> {
        let endpoint = "/api/analytics/servers/\(serverId)/metrics"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func getPlayerAnalytics() -> AnyPublisher<PlayerAnalytics, APIError> {
        let endpoint = "/api/analytics/players"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    // MARK: - Plugins
    
    func searchPlugins(query: String, filters: [String: Any]? = nil) -> AnyPublisher<[Plugin], APIError> {
        var endpoint = "/api/plugins/search?q=\(query)"
        if let filters = filters {
            for (key, value) in filters {
                endpoint += "&\(key)=\(value)"
            }
        }
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func getPluginDetails(pluginId: String) -> AnyPublisher<PluginDetails, APIError> {
        let endpoint = "/api/plugins/\(pluginId)"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func installPlugin(pluginId: String) -> AnyPublisher<PluginAction, APIError> {
        let endpoint = "/api/plugins/\(pluginId)/install"
        return request(endpoint: endpoint, method: "POST", body: nil as String?)
    }
    
    func uninstallPlugin(pluginId: String) -> AnyPublisher<PluginAction, APIError> {
        let endpoint = "/api/plugins/\(pluginId)/uninstall"
        return request(endpoint: endpoint, method: "POST", body: nil as String?)
    }
    
    // MARK: - Notifications
    
    func registerDevice(deviceToken: String) -> AnyPublisher<Void, APIError> {
        let endpoint = "/api/notifications/register"
        let body = ["deviceToken": deviceToken, "platform": "ios"]
        return request(endpoint: endpoint, method: "POST", body: body)
    }
    
    func getNotifications() -> AnyPublisher<[PanelNotification], APIError> {
        let endpoint = "/api/notifications"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func markNotificationRead(notificationId: String) -> AnyPublisher<Void, APIError> {
        let endpoint = "/api/notifications/\(notificationId)/read"
        return request(endpoint: endpoint, method: "PUT", body: nil as String?)
    }
    
    // MARK: - User Profile
    
    func getUserProfile() -> AnyPublisher<UserProfile, APIError> {
        let endpoint = "/api/user/profile"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func updateUserProfile(updates: ProfileUpdate) -> AnyPublisher<UserProfile, APIError> {
        let endpoint = "/api/user/profile"
        return request(endpoint: endpoint, method: "PUT", body: updates)
    }
    
    func changePassword(oldPassword: String, newPassword: String) -> AnyPublisher<Void, APIError> {
        let endpoint = "/api/user/password"
        let body = ["oldPassword": oldPassword, "newPassword": newPassword]
        return request(endpoint: endpoint, method: "POST", body: body)
    }
    
    // MARK: - Blockchain
    
    func getWalletBalance() -> AnyPublisher<WalletBalance, APIError> {
        let endpoint = "/api/blockchain/wallet/balance"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func getNFTAssets() -> AnyPublisher<[NFTAsset], APIError> {
        let endpoint = "/api/blockchain/nfts"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func mintAchievementNFT(achievementId: String) -> AnyPublisher<NFTAsset, APIError> {
        let endpoint = "/api/blockchain/nfts/mint"
        let body = ["achievementId": achievementId]
        return request(endpoint: endpoint, method: "POST", body: body)
    }
    
    // MARK: - Support
    
    func createSupportTicket(ticket: SupportTicketRequest) -> AnyPublisher<SupportTicket, APIError> {
        let endpoint = "/api/support/tickets"
        return request(endpoint: endpoint, method: "POST", body: ticket)
    }
    
    func getSupportTickets() -> AnyPublisher<[SupportTicket], APIError> {
        let endpoint = "/api/support/tickets"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    func searchKnowledgeBase(query: String) -> AnyPublisher<[KBArticle], APIError> {
        let endpoint = "/api/support/kb/search?q=\(query)"
        return request(endpoint: endpoint, method: "GET", body: nil as String?)
    }
    
    // MARK: - Generic Request Handler
    
    private func request<T: Decodable, B: Encodable>(
        endpoint: String,
        method: String,
        body: B?
    ) -> AnyPublisher<T, APIError> {
        guard let url = URL(string: baseURL + endpoint) else {
            return Fail(error: APIError.invalidURL).eraseToAnyPublisher()
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Add authentication token
        if let token = KeychainService.shared.getToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        // Encode body if present
        if let body = body {
            do {
                request.httpBody = try JSONEncoder().encode(body)
            } catch {
                return Fail(error: APIError.networkError(error)).eraseToAnyPublisher()
            }
        }
        
        return session.dataTaskPublisher(for: request)
            .tryMap { data, response -> Data in
                guard let httpResponse = response as? HTTPURLResponse else {
                    throw APIError.invalidResponse
                }
                
                switch httpResponse.statusCode {
                case 200...299:
                    return data
                case 401:
                    throw APIError.unauthorized
                case 400...499:
                    let errorMessage = String(data: data, encoding: .utf8) ?? "Client error"
                    throw APIError.serverError(errorMessage)
                case 500...599:
                    let errorMessage = String(data: data, encoding: .utf8) ?? "Server error"
                    throw APIError.serverError(errorMessage)
                default:
                    throw APIError.invalidResponse
                }
            }
            .decode(type: T.self, decoder: JSONDecoder())
            .mapError { error in
                if let apiError = error as? APIError {
                    return apiError
                } else if let decodingError = error as? DecodingError {
                    return APIError.serverError("Failed to decode response: \(decodingError)")
                } else {
                    return APIError.networkError(error)
                }
            }
            .receive(on: DispatchQueue.main)
            .eraseToAnyPublisher()
    }
}

// MARK: - Keychain Service

class KeychainService {
    static let shared = KeychainService()
    
    private let tokenKey = "com.panel.app.token"
    
    func saveToken(_ token: String) {
        let data = token.data(using: .utf8)!
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: tokenKey,
            kSecValueData as String: data
        ]
        
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    func getToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: tokenKey,
            kSecReturnData as String: true
        ]
        
        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)
        
        guard let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    
    func deleteToken() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: tokenKey
        ]
        
        SecItemDelete(query as CFDictionary)
    }
}