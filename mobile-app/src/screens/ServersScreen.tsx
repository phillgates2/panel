// mobile-app/src/screens/ServersScreen.tsx

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import apiService from '../services/ApiService';
import Swipeable from 'react-native-gesture-handler/Swipeable';
import HapticFeedback from 'react-native-haptic-feedback';

interface Server {
  id: string;
  name: string;
  game_type: string;
  status: string;
  player_count: number;
  max_players: number;
  cpu_usage: number;
  memory_usage: number;
  ip_address: string;
}

const ServersScreen: React.FC = ({ navigation }: any) => {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<'all' | 'running' | 'stopped'>('all');

  const fetchServers = useCallback(async () => {
    try {
      const data = await apiService.getServers();
      const normalized = (data || []).map((s: any) => apiService.normalizeServer(s));
      setServers(normalized);
    } catch (error) {
      console.error('Failed to fetch servers:', error);
      Alert.alert('Error', 'Failed to load servers');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchServers();
  }, [fetchServers]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchServers();
  }, [fetchServers]);

  const handleServerAction = async (serverId: string, action: 'start' | 'stop' | 'restart') => {
    HapticFeedback.trigger('impactMedium');
    
    try {
      switch (action) {
        case 'start':
          await apiService.startServer(serverId);
          break;
        case 'stop':
          await apiService.stopServer(serverId);
          break;
        case 'restart':
          await apiService.restartServer(serverId);
          break;
      }
      
      HapticFeedback.trigger('notificationSuccess');
      fetchServers();
    } catch (error) {
      HapticFeedback.trigger('notificationError');
      Alert.alert('Error', `Failed to ${action} server`);
    }
  };

  const handleDeleteServer = (serverId: string) => {
    Alert.alert(
      'Delete Server',
      'Are you sure you want to delete this server?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiService.deleteServer(serverId);
              HapticFeedback.trigger('notificationSuccess');
              fetchServers();
            } catch (error) {
              Alert.alert('Error', 'Failed to delete server');
            }
          },
        },
      ]
    );
  };

  const renderRightActions = (serverId: string) => {
    return (
      <View style={styles.swipeActionsContainer}>
        <TouchableOpacity
          style={[styles.swipeAction, { backgroundColor: '#FF3B30' }]}
          onPress={() => handleDeleteServer(serverId)}
        >
          <Icon name="delete" size={24} color="#FFF" />
          <Text style={styles.swipeActionText}>Delete</Text>
        </TouchableOpacity>
      </View>
    );
  };

  const renderServerCard = ({ item }: { item: Server }) => {
    const isRunning = item.status === 'running';
    const statusColor = isRunning ? '#4CAF50' : '#FF3B30';

    const cpu = typeof item.cpu_usage === 'number' ? item.cpu_usage : 0;
    const mem = typeof item.memory_usage === 'number' ? item.memory_usage : 0;

    return (
      <Swipeable renderRightActions={() => renderRightActions(item.id)}>
        <TouchableOpacity
          style={styles.serverCard}
          onPress={() => navigation.navigate('ServerDetails', { serverId: item.id })}
        >
          <View style={styles.serverHeader}>
            <View style={styles.serverTitleContainer}>
              <Icon name="server" size={24} color="#007AFF" style={styles.serverIcon} />
              <View>
                <Text style={styles.serverName}>{item.name}</Text>
                <Text style={styles.serverGameType}>{item.game_type}</Text>
              </View>
            </View>
            <View style={[styles.statusBadge, { backgroundColor: statusColor }]}>
              <Text style={styles.statusText}>{item.status}</Text>
            </View>
          </View>

          <View style={styles.serverStats}>
            <View style={styles.statItem}>
              <Icon name="account-group" size={20} color="#666" />
              <Text style={styles.statText}>
                {item.player_count}/{item.max_players}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Icon name="memory" size={20} color="#666" />
              <Text style={styles.statText}>{cpu.toFixed(1)}%</Text>
            </View>
            <View style={styles.statItem}>
              <Icon name="database" size={20} color="#666" />
              <Text style={styles.statText}>{mem.toFixed(1)}%</Text>
            </View>
          </View>

          <View style={styles.serverActions}>
            {isRunning ? (
              <>
                <TouchableOpacity
                  style={[styles.actionButton, { backgroundColor: '#FF9500' }]}
                  onPress={() => handleServerAction(item.id, 'restart')}
                >
                  <Icon name="restart" size={18} color="#FFF" />
                  <Text style={styles.actionButtonText}>Restart</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.actionButton, { backgroundColor: '#FF3B30' }]}
                  onPress={() => handleServerAction(item.id, 'stop')}
                >
                  <Icon name="stop" size={18} color="#FFF" />
                  <Text style={styles.actionButtonText}>Stop</Text>
                </TouchableOpacity>
              </>
            ) : (
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#4CAF50' }]}
                onPress={() => handleServerAction(item.id, 'start')}
              >
                <Icon name="play" size={18} color="#FFF" />
                <Text style={styles.actionButtonText}>Start</Text>
              </TouchableOpacity>
            )}
          </View>
        </TouchableOpacity>
      </Swipeable>
    );
  };

  const filteredServers = servers.filter((server) => {
    if (filter === 'all') return true;
    if (filter === 'running') return server.status === 'running';
    if (filter === 'stopped') return server.status === 'stopped';
    return true;
  });

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.filterContainer}>
        <TouchableOpacity
          style={[styles.filterButton, filter === 'all' && styles.filterButtonActive]}
          onPress={() => setFilter('all')}
        >
          <Text style={[styles.filterButtonText, filter === 'all' && styles.filterButtonTextActive]}>
            All ({servers.length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterButton, filter === 'running' && styles.filterButtonActive]}
          onPress={() => setFilter('running')}
        >
          <Text style={[styles.filterButtonText, filter === 'running' && styles.filterButtonTextActive]}>
            Running ({servers.filter(s => s.status === 'running').length})
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterButton, filter === 'stopped' && styles.filterButtonActive]}
          onPress={() => setFilter('stopped')}
        >
          <Text style={[styles.filterButtonText, filter === 'stopped' && styles.filterButtonTextActive]}>
            Stopped ({servers.filter(s => s.status === 'stopped').length})
          </Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={filteredServers}
        renderItem={renderServerCard}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Icon name="server-off" size={64} color="#CCC" />
            <Text style={styles.emptyText}>No servers found</Text>
            <TouchableOpacity
              style={styles.createButton}
              onPress={() => navigation.navigate('CreateServer')}
            >
              <Icon name="plus" size={20} color="#FFF" />
              <Text style={styles.createButtonText}>Create Server</Text>
            </TouchableOpacity>
          </View>
        }
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('CreateServer')}
      >
        <Icon name="plus" size={28} color="#FFF" />
      </TouchableOpacity>
    </View>
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
  },
  filterContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  filterButton: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    marginHorizontal: 4,
    borderRadius: 8,
    backgroundColor: '#F0F0F0',
    alignItems: 'center',
  },
  filterButtonActive: {
    backgroundColor: '#007AFF',
  },
  filterButtonText: {
    fontSize: 14,
    color: '#666',
    fontWeight: '600',
  },
  filterButtonTextActive: {
    color: '#FFF',
  },
  listContainer: {
    padding: 16,
  },
  serverCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  serverHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  serverTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  serverIcon: {
    marginRight: 12,
  },
  serverName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  serverGameType: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  statusBadge: {
    paddingVertical: 4,
    paddingHorizontal: 12,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    color: '#FFF',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  serverStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#F0F0F0',
    marginBottom: 12,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 6,
  },
  serverActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    marginLeft: 8,
  },
  actionButtonText: {
    fontSize: 14,
    color: '#FFF',
    fontWeight: '600',
    marginLeft: 4,
  },
  swipeActionsContainer: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  swipeAction: {
    width: 80,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
    marginLeft: 8,
  },
  swipeActionText: {
    fontSize: 12,
    color: '#FFF',
    fontWeight: '600',
    marginTop: 4,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 16,
    marginBottom: 24,
  },
  createButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 24,
  },
  createButtonText: {
    fontSize: 16,
    color: '#FFF',
    fontWeight: '600',
    marginLeft: 8,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
  },
});

export default ServersScreen;