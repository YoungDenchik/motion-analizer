import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  SERVER_URL: '@ai_trainer:server_url',
  TOKEN: '@ai_trainer:token',
  USER: '@ai_trainer:user',
} as const;

export const storage = {
  async saveServerUrl(url: string): Promise<void> {
    await AsyncStorage.setItem(KEYS.SERVER_URL, url);
  },
  async getServerUrl(): Promise<string | null> {
    return AsyncStorage.getItem(KEYS.SERVER_URL);
  },

  async saveToken(token: string): Promise<void> {
    await AsyncStorage.setItem(KEYS.TOKEN, token);
  },
  async getToken(): Promise<string | null> {
    return AsyncStorage.getItem(KEYS.TOKEN);
  },

  async saveUser(user: object): Promise<void> {
    await AsyncStorage.setItem(KEYS.USER, JSON.stringify(user));
  },
  async getUser<T>(): Promise<T | null> {
    const raw = await AsyncStorage.getItem(KEYS.USER);
    return raw ? (JSON.parse(raw) as T) : null;
  },

  async clearAuth(): Promise<void> {
    await AsyncStorage.multiRemove([KEYS.TOKEN, KEYS.USER]);
  },

  async clearAll(): Promise<void> {
    await AsyncStorage.multiRemove(Object.values(KEYS));
  },
};
