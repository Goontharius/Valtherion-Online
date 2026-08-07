import axios from 'axios';
import { NativeModules } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// In development, derive the backend host from the Metro bundler's host, so a
// physical phone on the same Wi-Fi naturally reaches the dev machine without
// hardcoding an IP. Falls back to localhost (emulator) if detection fails.
let devHost = 'localhost';
try {
  const host = NativeModules.SourceCode?.scriptURL?.match(/^https?:\/\/([^/:]+)/)?.[1];
  if (host) devHost = host;
} catch (e) { /* fall back to localhost */ }

const API_BASE_URL = __DEV__
  ? `http://${devHost}:8000`
  : 'https://api.valtheriononline.com';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = await AsyncStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/refresh`, {
            refresh_token: refreshToken,
          });
          await AsyncStorage.setItem('auth_token', response.data.access_token);
          await AsyncStorage.setItem('refresh_token', response.data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          await AsyncStorage.removeItem('auth_token');
          await AsyncStorage.removeItem('refresh_token');
        }
      }
    }

    return Promise.reject(error);
  }
);

export default api;
