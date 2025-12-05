// mobile-app/src/screens/DashboardScreen.tsx

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { LineChart, BarChart, PieChart } from 'react-native-chart-kit';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import LinearGradient from 'react-native-linear-gradient';
import apiService from '../services/ApiService';

const { width } = Dimensions.get('window');

interface DashboardStats {
  totalServers: number;
  activeServers: number;
  totalPlayers: number;
  avgCpuUsage: number;
  avgMemoryUsage: number;
  alerts: any[];
}

const DashboardScreen: React.FC = ({ navigation }: any) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [performanceData, setPerformanceData] = useState<any>(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [serversData, analyticsData] = await Promise.all([
        apiService.getServers(),
        apiService.getAnalytics('24h'),
      ]);

      const activeServers = serversData.filter((s: any) => s.status === 'running');
      const totalPlayers = serversData.reduce((sum: number, s: any) => sum + s.playerCount, 0);

      setStats({
        totalServers: serversData.length,
        activeServers: activeServers.length,
        totalPlayers,
        avgCpuUsage: analyticsData.avgCpuUsage || 0,
        avgMemoryUsage: analyticsData.avgMemoryUsage || 0,
        alerts: analyticsData.alerts || [],
      });

      setPerformanceData(analyticsData.performanceHistory || []);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
    
    // Set up auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDashboardData();
  }, [fetchDashboardData]);

  const renderStatCard = (
    icon: string,
    label: string,
    value: string | number,
    color: string,
    onPress?: () => void
  ) => (
    <TouchableOpacity
      style={[styles.statCard, { borderLeftColor: color }]}
      onPress={onPress}
      disabled={!onPress}
    >
      <View style={styles.statCardContent}>
        <View style={[styles.iconContainer, { backgroundColor: color + '20' }]}>
          <Icon name={icon} size={28} color={color} />
        </View>
        <View style={styles.statTextContainer}>
          <Text style={styles.statValue}>{value}</Text>
          <Text style={styles.statLabel}>{label}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  const renderPerformanceChart = () => {
    if (!performanceData || performanceData.length === 0) {
      return null;
    }

    const chartData = {
      labels: performanceData.map((d: any) => new Date(d.timestamp).getHours() + 'h'),
      datasets: [
        {
          data: performanceData.map((d: any) => d.cpuUsage),
          color: (opacity = 1) => `rgba(255, 99, 71, ${opacity})`,
          strokeWidth: 2,
        },
        {
          data: performanceData.map((d: any) => d.memoryUsage),
          color: (opacity = 1) => `rgba(54, 162, 235, ${opacity})`,
          strokeWidth: 2,
        },
      ],
      legend: ['CPU Usage', 'Memory Usage'],
    };

    return (
      <View style={styles.chartContainer}>
        <Text style={styles.chartTitle}>Performance Over Time</Text>
        <LineChart
          data={chartData}
          width={width - 40}
          height={220}
          chartConfig={{
            backgroundColor: '#ffffff',
            backgroundGradientFrom: '#ffffff',
            backgroundGradientTo: '#ffffff',
            decimalPlaces: 1,
            color: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
            labelColor: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
            style: {
              borderRadius: 16,
            },
            propsForDots: {
              r: '4',
              strokeWidth: '2',
            },
          }}
          bezier
          style={styles.chart}
        />
      </View>
    );
  };

  const renderAlerts = () => {
    if (!stats || stats.alerts.length === 0) {
      return null;
    }

    return (
      <View style={styles.alertsContainer}>
        <Text style={styles.sectionTitle}>Recent Alerts</Text>
        {stats.alerts.slice(0, 3).map((alert: any, index: number) => (
          <View key={index} style={[styles.alertCard, { borderLeftColor: getAlertColor(alert.severity) }]}>
            <Icon
              name={getAlertIcon(alert.severity)}
              size={24}
              color={getAlertColor(alert.severity)}
              style={styles.alertIcon}
            />
            <View style={styles.alertContent}>
              <Text style={styles.alertTitle}>{alert.title}</Text>
              <Text style={styles.alertMessage}>{alert.message}</Text>
              <Text style={styles.alertTime}>
                {new Date(alert.timestamp).toLocaleTimeString()}
              </Text>
            </View>
          </View>
        ))}
        {stats.alerts.length > 3 && (
          <TouchableOpacity
            style={styles.viewAllButton}
            onPress={() => navigation.navigate('Alerts')}
          >
            <Text style={styles.viewAllText}>View All Alerts ({stats.alerts.length})</Text>
            <Icon name="chevron-right" size={20} color="#007AFF" />
          </TouchableOpacity>
        )}
      </View>
    );
  };

  const getAlertColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return '#FF3B30';
      case 'warning':
        return '#FF9500';
      case 'info':
        return '#007AFF';
      default:
        return '#8E8E93';
    }
  };

  const getAlertIcon = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return 'alert-circle';
      case 'warning':
        return 'alert';
      case 'info':
        return 'information';
      default:
        return 'bell';
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading Dashboard...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <LinearGradient
        colors={['#4c669f', '#3b5998', '#192f6a']}
        style={styles.header}
      >
        <Text style={styles.headerTitle}>Dashboard</Text>
        <Text style={styles.headerSubtitle}>Panel Gaming Platform</Text>
      </LinearGradient>

      <View style={styles.content}>
        {/* Quick Stats */}
        <View style={styles.statsGrid}>
          {renderStatCard(
            'server-network',
            'Total Servers',
            stats?.totalServers || 0,
            '#4CAF50',
            () => navigation.navigate('Servers')
          )}
          {renderStatCard(
            'play-circle',
            'Active Servers',
            stats?.activeServers || 0,
            '#2196F3'
          )}
          {renderStatCard(
            'account-group',
            'Total Players',
            stats?.totalPlayers || 0,
            '#FF9800'
          )}
          {renderStatCard(
            'memory',
            'Avg CPU',
            `${stats?.avgCpuUsage.toFixed(1)}%` || '0%',
            '#9C27B0'
          )}
        </View>

        {/* Performance Chart */}
        {renderPerformanceChart()}

        {/* Recent Alerts */}
        {renderAlerts()}

        {/* Quick Actions */}
        <View style={styles.quickActionsContainer}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.quickActionsGrid}>
            <TouchableOpacity
              style={styles.quickActionButton}
              onPress={() => navigation.navigate('CreateServer')}
            >
              <Icon name="plus-circle" size={32} color="#4CAF50" />
              <Text style={styles.quickActionText}>New Server</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.quickActionButton}
              onPress={() => navigation.navigate('Analytics')}
            >
              <Icon name="chart-line" size={32} color="#2196F3" />
              <Text style={styles.quickActionText}>Analytics</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.quickActionButton}
              onPress={() => navigation.navigate('Plugins')}
            >
              <Icon name="puzzle" size={32} color="#FF9800" />
              <Text style={styles.quickActionText}>Plugins</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.quickActionButton}
              onPress={() => navigation.navigate('Settings')}
            >
              <Icon name="cog" size={32} color="#9C27B0" />
              <Text style={styles.quickActionText}>Settings</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  header: {
    padding: 20,
    paddingTop: 50,
    paddingBottom: 30,
  },
  headerTitle: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 5,
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#FFFFFF',
    opacity: 0.8,
  },
  content: {
    padding: 16,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  statCard: {
    width: '48%',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  statCardContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  statTextContainer: {
    flex: 1,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 2,
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
  },
  chartContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  chartTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  alertsContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  alertCard: {
    flexDirection: 'row',
    padding: 12,
    borderLeftWidth: 4,
    backgroundColor: '#F9F9F9',
    borderRadius: 8,
    marginBottom: 10,
  },
  alertIcon: {
    marginRight: 12,
  },
  alertContent: {
    flex: 1,
  },
  alertTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  alertMessage: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  alertTime: {
    fontSize: 10,
    color: '#999',
  },
  viewAllButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    marginTop: 8,
  },
  viewAllText: {
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '600',
    marginRight: 4,
  },
  quickActionsContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  quickActionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  quickActionButton: {
    width: '48%',
    aspectRatio: 1,
    backgroundColor: '#F9F9F9',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  quickActionText: {
    fontSize: 12,
    color: '#333',
    fontWeight: '600',
    marginTop: 8,
  },
});

export default DashboardScreen;