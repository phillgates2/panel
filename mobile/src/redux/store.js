/**
 * Redux Store Configuration
 *
 * Centralized state management for the Panel mobile app.
 */

import {configureStore} from '@reduxjs/toolkit';
import {persistStore, persistReducer} from 'redux-persist';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {combineReducers} from 'redux';

// Import reducers
import authReducer from './slices/authSlice';
import serversReducer from './slices/serversSlice';
import chatReducer from './slices/chatSlice';
import notificationsReducer from './slices/notificationsSlice';
import themeReducer from './slices/themeSlice';
import uiReducer from './slices/uiSlice';

// Persist configuration
const persistConfig = {
  key: 'root',
  storage: AsyncStorage,
  whitelist: ['auth', 'theme', 'servers'], // Only persist these slices
  blacklist: ['ui'], // Don't persist UI state
};

// Root reducer
const rootReducer = combineReducers({
  auth: authReducer,
  servers: serversReducer,
  chat: chatReducer,
  notifications: notificationsReducer,
  theme: themeReducer,
  ui: uiReducer,
});

// Persisted reducer
const persistedReducer = persistReducer(persistConfig, rootReducer);

// Store configuration
export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }),
  devTools: __DEV__, // Enable Redux DevTools in development
});

// Persistor for redux-persist
export const persistor = persistStore(store);

// Type definitions for TypeScript support
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;