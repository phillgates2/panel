import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, SafeAreaView, StyleSheet, View } from 'react-native';

import LoginScreen from './src/screens/LoginScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import apiService from './src/services/ApiService';

type AuthState = 'loading' | 'logged_out' | 'logged_in';

export default function App() {
  const [authState, setAuthState] = useState<AuthState>('loading');

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const loggedIn = await apiService.isLoggedIn();
        if (!cancelled) {
          setAuthState(loggedIn ? 'logged_in' : 'logged_out');
        }
      } catch {
        if (!cancelled) setAuthState('logged_out');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const navigationStub = useMemo(
    () => ({
      navigate: () => {
        // No navigation in the minimal scaffold.
      },
      goBack: () => {
        // No navigation in the minimal scaffold.
      },
    }),
    []
  );

  if (authState === 'loading') {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
      </SafeAreaView>
    );
  }

  if (authState === 'logged_out') {
    return <LoginScreen onLoggedIn={() => setAuthState('logged_in')} />;
  }

  return (
    <View style={styles.container}>
      <DashboardScreen navigation={navigationStub} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
