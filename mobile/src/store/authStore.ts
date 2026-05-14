import { create } from 'zustand';
import { storage } from '../services/storage';

interface AuthState {
  isAuthenticated: boolean;
  serverUrl: string;
  userName: string;
  isLoading: boolean;
  initialize: () => Promise<void>;
  login: (serverUrl: string, userName: string) => Promise<void>;
  logout: () => Promise<void>;
  updateServerUrl: (url: string) => Promise<void>;
  updateUserName: (name: string) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  serverUrl: '',
  userName: '',
  isLoading: true,

  initialize: async () => {
    const [authenticated, serverUrl, userName] = await Promise.all([
      storage.isAuthenticated(),
      storage.getServerUrl(),
      storage.getUserName(),
    ]);
    set({
      isAuthenticated: authenticated,
      serverUrl: serverUrl ?? '',
      userName: userName ?? '',
      isLoading: false,
    });
  },

  login: async (serverUrl, userName) => {
    await Promise.all([
      storage.saveServerUrl(serverUrl),
      storage.saveUserName(userName),
      storage.setAuthenticated(true),
    ]);
    set({ isAuthenticated: true, serverUrl, userName });
  },

  logout: async () => {
    await storage.clearAll();
    set({ isAuthenticated: false, serverUrl: '', userName: '' });
  },

  updateServerUrl: async (url) => {
    await storage.saveServerUrl(url);
    set({ serverUrl: url });
  },

  updateUserName: async (name) => {
    await storage.saveUserName(name);
    set({ userName: name });
  },
}));
