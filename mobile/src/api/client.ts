import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';

function getApiBase(): string {
  return `${useAuthStore.getState().serverUrl}/api`;
}

function injectHeaders(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  if (!config.baseURL) config.baseURL = getApiBase();
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
}

function normalizeError(error: AxiosError): never {
  if (error.response?.status === 401) {
    // Token expired or invalid — clear auth state
    useAuthStore.getState().logout();
  }
  if (error.response) {
    const data = error.response.data as { detail?: string; message?: string };
    const message = data?.detail ?? data?.message ?? `Server error ${error.response.status}`;
    throw new Error(message);
  }
  if (error.request) {
    throw new Error('Cannot reach the server. Check your network and the server URL.');
  }
  throw new Error(error.message ?? 'Unknown error');
}

export const apiClient = axios.create({ timeout: 30_000 });
apiClient.interceptors.request.use(injectHeaders);
apiClient.interceptors.response.use((r) => r, (e: AxiosError) => normalizeError(e));

// Separate client for video uploads — longer timeout, upload progress support
export const uploadClient = axios.create({ timeout: 300_000 });
uploadClient.interceptors.request.use(injectHeaders);
uploadClient.interceptors.response.use((r) => r, (e: AxiosError) => normalizeError(e));
