/**
 * Panel Mobile App
 *
 * React Native mobile application for Panel game server management platform.
 * Provides mobile access to server monitoring, management, and community features.
 */

import React from 'react';
import {StatusBar, StyleSheet} from 'react-native';
import {Provider} from 'react-redux';
import {PersistGate} from 'redux-persist/integration/react';
import {NavigationContainer} from '@react-navigation/native';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import Toast from 'react-native-toast-message';

import {store, persistor} from './src/redux/store';
import AppNavigator from './src/navigation/AppNavigator';
import {ThemeProvider} from './src/context/ThemeContext';
import {AuthProvider} from './src/context/AuthContext';
import {NotificationProvider} from './src/context/NotificationContext';

const App = () => {
  return (
    <Provider store={store}>
      <PersistGate loading={null} persistor={persistor}>
        <SafeAreaProvider>
          <ThemeProvider>
            <AuthProvider>
              <NotificationProvider>
                <NavigationContainer>
                  <StatusBar
                    barStyle="light-content"
                    backgroundColor="#1a1a1a"
                  />
                  <AppNavigator />
                  <Toast />
                </NavigationContainer>
              </NotificationProvider>
            </AuthProvider>
          </ThemeProvider>
        </SafeAreaProvider>
      </PersistGate>
    </Provider>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});

export default App;