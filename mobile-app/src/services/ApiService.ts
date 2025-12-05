// mobile-app/src/services/ApiService.ts

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface ApiConfig {
  baseURL: string;
  timeout: number;
}

class ApiService {
  private api: AxiosInstance;
  private wsConnection: WebSocket | null = null;

  constructor(config: ApiConfig) {
    this.api = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.api.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          await AsyncStorage.removeItem('auth_token');
          // Navigate to login screen
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication APIs
  async login(username: string, password: string): Promise<any> {
    const response = await this.api.post('/api/auth/login', {
      username,
      password,
    });
    
    if (response.data.token) {
      await AsyncStorage.setItem('auth_token', response.data.token);
    }
    
    return response.data;
  }

  async logout(): Promise<void> {
    await this.api.post('/api/auth/logout');
    await AsyncStorage.removeItem('auth_token');
  }

  async register(userData: any): Promise<any> {
    const response = await this.api.post('/api/auth/register', userData);
    return response.data;
  }

  // Server Management APIs
  async getServers(): Promise<any[]> {
    const response = await this.api.get('/api/servers');
    return response.data;
  }

  async getServerDetails(serverId: string): Promise<any> {
    const response = await this.api.get(`/api/servers/${serverId}`);
    return response.data;
  }

  async createServer(serverConfig: any): Promise<any> {
    const response = await this.api.post('/api/servers', serverConfig);
    return response.data;
  }

  async updateServer(serverId: string, updates: any): Promise<any> {
    const response = await this.api.put(`/api/servers/${serverId}`, updates);
    return response.data;
  }

  async deleteServer(serverId: string): Promise<void> {
    await this.api.delete(`/api/servers/${serverId}`);
  }

  async startServer(serverId: string): Promise<any> {
    const response = await this.api.post(`/api/servers/${serverId}/start`);
    return response.data;
  }

  async stopServer(serverId: string): Promise<any> {
    const response = await this.api.post(`/api/servers/${serverId}/stop`);
    return response.data;
  }

  async restartServer(serverId: string): Promise<any> {
    const response = await this.api.post(`/api/servers/${serverId}/restart`);
    return response.data;
  }

  // Analytics APIs
  async getAnalytics(timeRange: string = '24h'): Promise<any> {
    const response = await this.api.get('/api/analytics/dashboard', {
      params: { timeRange },
    });
    return response.data;
  }

  async getServerMetrics(serverId: string): Promise<any> {
    const response = await this.api.get(`/api/analytics/servers/${serverId}/metrics`);
    return response.data;
  }

  async getPlayerAnalytics(): Promise<any> {
    const response = await this.api.get('/api/analytics/players');
    return response.data;
  }

  // Plugin Marketplace APIs
  async searchPlugins(query: string, filters?: any): Promise<any[]> {
    const response = await this.api.get('/api/plugins/search', {
      params: { q: query, ...filters },
    });
    return response.data;
  }

  async getPluginDetails(pluginId: string): Promise<any> {
    const response = await this.api.get(`/api/plugins/${pluginId}`);
    return response.data;
  }

  async installPlugin(pluginId: string): Promise<any> {
    const response = await this.api.post(`/api/plugins/${pluginId}/install`);
    return response.data;
  }

  async uninstallPlugin(pluginId: string): Promise<any> {
    const response = await this.api.post(`/api/plugins/${pluginId}/uninstall`);
    return response.data;
  }

  // Notification APIs
  async registerDevice(deviceToken: string): Promise<void> {
    await this.api.post('/api/notifications/register', {
      deviceToken,
      platform: Platform.OS,
    });
  }

  async getNotifications(): Promise<any[]> {
    const response = await this.api.get('/api/notifications');
    return response.data;
  }

  async markNotificationRead(notificationId: string): Promise<void> {
    await this.api.put(`/api/notifications/${notificationId}/read`);
  }

  // User Profile APIs
  async getUserProfile(): Promise<any> {
    const response = await this.api.get('/api/user/profile');
    return response.data;
  }

  async updateUserProfile(updates: any): Promise<any> {
    const response = await this.api.put('/api/user/profile', updates);
    return response.data;
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.api.post('/api/user/password', {
      oldPassword,
      newPassword,
    });
  }

  // Blockchain APIs
  async getWalletBalance(): Promise<any> {
    const response = await this.api.get('/api/blockchain/wallet/balance');
    return response.data;
  }

  async getNFTAssets(): Promise<any[]> {
    const response = await this.api.get('/api/blockchain/nfts');
    return response.data;
  }

  async mintAchievementNFT(achievementId: string): Promise<any> {
    const response = await this.api.post('/api/blockchain/nfts/mint', {
      achievementId,
    });
    return response.data;
  }

  // Support APIs
  async createSupportTicket(ticket: any): Promise<any> {
    const response = await this.api.post('/api/support/tickets', ticket);
    return response.data;
  }

  async getSupportTickets(): Promise<any[]> {
    const response = await this.api.get('/api/support/tickets');
    return response.data;
  }

  async searchKnowledgeBase(query: string): Promise<any[]> {
    const response = await this.api.get('/api/support/kb/search', {
      params: { q: query },
    });
    return response.data;
  }

  // WebSocket Connection
  connectWebSocket(token: string): void {
    const wsUrl = this.api.defaults.baseURL?.replace('http', 'ws') + '/ws';
    this.wsConnection = new WebSocket(wsUrl);

    this.wsConnection.onopen = () => {
      console.log('WebSocket connected');
      this.wsConnection?.send(JSON.stringify({ type: 'auth', token }));
    };

    this.wsConnection.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleWebSocketMessage(data);
    };

    this.wsConnection.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.wsConnection.onclose = () => {
      console.log('WebSocket disconnected');
      // Attempt reconnection
      setTimeout(() => this.connectWebSocket(token), 5000);
    };
  }

  disconnectWebSocket(): void {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }

  private handleWebSocketMessage(data: any): void {
    // Handle real-time updates
    switch (data.type) {
      case 'server_update':
        // Dispatch to Redux store
        break;
      case 'notification':
        // Show push notification
        break;
      case 'alert':
        // Handle alert
        break;
      default:
        console.log('Unknown WebSocket message:', data);
    }
  }

  // File Upload
  async uploadFile(file: any, endpoint: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.api.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }
}

// Create singleton instance
const apiService = new ApiService({
  baseURL: __DEV__ ? 'http://localhost:5000' : 'https://api.panel.dev',
  timeout: 30000,
});

export default apiService;