import AsyncStorage from '@react-native-async-storage/async-storage';
import type { HistoryEntry, AnalysisResult } from '../types/api';

const KEY = 'analysis_history_v1';
const MAX = 50;

export async function saveToHistory(exercise: string, result: AnalysisResult): Promise<void> {
  const entry: HistoryEntry = {
    id: `${Date.now()}_${Math.random().toString(36).slice(2)}`,
    exercise,
    date: new Date().toISOString(),
    result: { ...result, has_annotated_video: false },
  };
  const list = await loadHistory();
  await AsyncStorage.setItem(KEY, JSON.stringify([entry, ...list].slice(0, MAX)));
}

export async function loadHistory(): Promise<HistoryEntry[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function clearHistory(): Promise<void> {
  await AsyncStorage.removeItem(KEY);
}
