import { create } from 'zustand';
import { storage } from '../services/storage';
import type { User } from '../types/api';

interface AuthState {
  isLoading: boolean;
  serverUrl: string;
  token: string | null;
  user: User | null;

  initialize: () => Promise<void>;
  setServerUrl: (url: string) => Promise<void>;
  loginSuccess: (token: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isLoading: true,
  serverUrl: '',
  token: null,
  user: null,

  initialize: async () => {
    const [serverUrl, token, user] = await Promise.all([
      storage.getServerUrl(),
      storage.getToken(),
      storage.getUser<User>(),
    ]);
    set({
      serverUrl: serverUrl ?? '',
      token,
      user,
      isLoading: false,
    });
  },

  setServerUrl: async (url) => {
    await storage.saveServerUrl(url);
    set({ serverUrl: url });
  },

  loginSuccess: async (token, user) => {
    await Promise.all([storage.saveToken(token), storage.saveUser(user)]);
    set({ token, user });
  },

  logout: async () => {
    await storage.clearAuth();
    set({ token: null, user: null });
  },
}));
