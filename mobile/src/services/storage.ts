import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  SERVER_URL: '@ai_trainer:server_url',
  USER_NAME: '@ai_trainer:user_name',
  IS_AUTHENTICATED: '@ai_trainer:is_authenticated',
} as const;

export const storage = {
  async saveServerUrl(url: string): Promise<void> {
    await AsyncStorage.setItem(KEYS.SERVER_URL, url);
  },

  async getServerUrl(): Promise<string | null> {
    return AsyncStorage.getItem(KEYS.SERVER_URL);
  },

  async saveUserName(name: string): Promise<void> {
    await AsyncStorage.setItem(KEYS.USER_NAME, name);
  },

  async getUserName(): Promise<string | null> {
    return AsyncStorage.getItem(KEYS.USER_NAME);
  },

  async setAuthenticated(value: boolean): Promise<void> {
    await AsyncStorage.setItem(KEYS.IS_AUTHENTICATED, String(value));
  },

  async isAuthenticated(): Promise<boolean> {
    const val = await AsyncStorage.getItem(KEYS.IS_AUTHENTICATED);
    return val === 'true';
  },

  async clearAll(): Promise<void> {
    await AsyncStorage.multiRemove(Object.values(KEYS));
  },
};
