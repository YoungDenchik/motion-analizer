import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Button } from '../../components/common/Button';
import { loadHistory, clearHistory } from '../../services/historyStorage';
import type { HistoryEntry } from '../../types/api';

function gradeColor(grade: string): string {
  if (grade.startsWith('A')) return '#4ade80';
  if (grade.startsWith('B')) return '#60a5fa';
  if (grade.startsWith('C')) return '#facc15';
  return '#f87171';
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) +
    '  ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export const HistoryScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const [entries, setEntries] = useState<HistoryEntry[]>([]);

  useFocusEffect(useCallback(() => {
    loadHistory().then(setEntries);
  }, []));

  const handleClear = () => {
    Alert.alert('Clear History', 'Remove all analysis history? This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Clear',
        style: 'destructive',
        onPress: async () => {
          await clearHistory();
          setEntries([]);
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <FlatList
        data={entries}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          entries.length > 0 ? (
            <Button label="Clear History" onPress={handleClear} variant="danger" style={styles.clearBtn} />
          ) : null
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>📋</Text>
            <Text style={styles.emptyTitle}>No history yet</Text>
            <Text style={styles.emptySubtitle}>Analyze a video to see your results here</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            activeOpacity={0.75}
            onPress={() => navigation.navigate('HistoryDetail', { entry: item })}
          >
            <View style={styles.card}>
              <View style={styles.cardLeft}>
                <Text style={styles.exercise}>{item.exercise}</Text>
                <Text style={styles.date}>{formatDate(item.date)}</Text>
                <Text style={styles.reps}>{item.result.num_reps} rep{item.result.num_reps !== 1 ? 's' : ''}</Text>
              </View>
              <View style={styles.cardRight}>
                <Text style={[styles.grade, { color: gradeColor(item.result.grade) }]}>
                  {item.result.grade}
                </Text>
                <Text style={styles.score}>{item.result.overall_score.toFixed(0)}</Text>
              </View>
            </View>
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={styles.sep} />}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  list: { padding: SPACING.md, gap: SPACING.sm },
  clearBtn: { marginBottom: SPACING.md },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cardLeft: { flex: 1, gap: 2 },
  exercise: { color: COLORS.text, fontSize: FONT_SIZE.md, fontWeight: '600', textTransform: 'capitalize' },
  date: { color: COLORS.textMuted, fontSize: FONT_SIZE.xs },
  reps: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginTop: 2 },
  cardRight: { alignItems: 'center', gap: 2 },
  grade: { fontSize: FONT_SIZE.xl, fontWeight: '700' },
  score: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm },
  sep: { height: SPACING.xs },
  empty: { alignItems: 'center', paddingVertical: SPACING.xxl, gap: SPACING.sm },
  emptyIcon: { fontSize: 48 },
  emptyTitle: { color: COLORS.text, fontSize: FONT_SIZE.lg, fontWeight: '600' },
  emptySubtitle: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, textAlign: 'center' },
});
