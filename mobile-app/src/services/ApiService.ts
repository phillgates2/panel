// mobile-app/src/services/ApiService.ts

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

interface ApiConfig {
  baseURL: string;
  timeout: number;
}

const ACCESS_TOKEN_KEY = 'auth_access_token';
const REFRESH_TOKEN_KEY = 'auth_refresh_token';

class ApiService {
  private api: AxiosInstance;
  private wsConnection: WebSocket | null = null;
  private isRefreshingToken: boolean = false;
  private refreshPromise: Promise<string> | null = null;

  async getAccessToken(): Promise<string | null> {
    return AsyncStorage.getItem(ACCESS_TOKEN_KEY);
  }

  async isLoggedIn(): Promise<boolean> {
    const token = await this.getAccessToken();
    return Boolean(token);
  }

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
        const token = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
        if (token && config.headers) {
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
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest?._retry) {
          originalRequest._retry = true;

          const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
          if (refreshToken) {
            try {
              const newAccessToken = await this.refreshAccessToken(refreshToken);
              originalRequest.headers = {
                ...(originalRequest.headers || {}),
                Authorization: `Bearer ${newAccessToken}`,
              };
              return this.api(originalRequest);
            } catch {
              await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY]);
            }
          } else {
            await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY]);
          }
        }
        return Promise.reject(error);
      }
    );
  }

  private async refreshAccessToken(refreshToken: string): Promise<string> {
    if (this.isRefreshingToken && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshingToken = true;
    this.refreshPromise = (async () => {
      const baseURL = this.api.defaults.baseURL || '';
      const response = await axios.post(
        `${baseURL}/auth/jwt/refresh`,
        {},
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${refreshToken}`,
          },
          timeout: this.api.defaults.timeout,
        }
      );

      const newAccessToken = response.data?.access_token;
      if (!newAccessToken) {
        throw new Error('Missing access_token in refresh response');
      }

      await AsyncStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken);
      return newAccessToken;
    })();

    try {
      return await this.refreshPromise;
    } finally {
      this.isRefreshingToken = false;
      this.refreshPromise = null;
    }
  }

  // Authentication APIs
  async login(email: string, password: string): Promise<any> {
    const response = await this.api.post('/auth/jwt/login', {
      email,
      password,
    });

    const accessToken = response.data?.access_token;
    const refreshToken = response.data?.refresh_token;

    if (accessToken) {
      await AsyncStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    }
    if (refreshToken) {
      await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }

    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/auth/jwt/logout');
    } finally {
      await AsyncStorage.multiRemove([ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY]);
    }
  }

  async register(userData: any): Promise<any> {
    const response = await this.api.post('/api/auth/register', userData);
    return response.data;
  }

  // Server Management APIs
  async getServers(): Promise<any[]> {
    const response = await this.api.get('/api/v2/servers');
    return response.data?.servers ?? [];
  }

  async getServerDetails(serverId: string): Promise<any> {
    const response = await this.api.get(`/api/v2/servers/${serverId}`);
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
    const response = await this.api.get(`/api/v2/servers/${serverId}/metrics`);
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
    const baseUrl = this.api.defaults.baseURL || '';
    const wsUrl = baseUrl.replace(/^http/, 'ws') + '/ws';
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

  // Helpers (used by screens to tolerate API shape differences)
  normalizeServer(raw: any): any {
    if (!raw || typeof raw !== 'object') return raw;
    const metrics = raw.metrics && typeof raw.metrics === 'object' ? raw.metrics : undefined;
    return {
      ...raw,
      status: raw.status ?? raw.state ?? 'unknown',
      player_count: raw.player_count ?? raw.playerCount ?? metrics?.player_count ?? metrics?.playerCount ?? 0,
      max_players: raw.max_players ?? raw.maxPlayers ?? 0,
      cpu_usage: raw.cpu_usage ?? raw.cpuUsage ?? metrics?.cpu_usage ?? metrics?.cpuUsage ?? 0,
      memory_usage: raw.memory_usage ?? raw.memoryUsage ?? metrics?.memory_usage ?? metrics?.memoryUsage ?? 0,
      game_type: raw.game_type ?? raw.gameType ?? raw.game ?? '',
    };
  }
}

// Create singleton instance
const apiService = new ApiService({
  baseURL:
    __DEV__ && Platform.OS === 'android'
      ? 'http://10.0.2.2:5000'
      : __DEV__
        ? 'http://localhost:5000'
        : 'https://api.panel.dev',
  timeout: 30000,
});

export default apiService;