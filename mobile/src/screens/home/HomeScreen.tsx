import React, { useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { COLORS, SPACING, FONT_SIZE } from '../../constants';
import { Card } from '../../components/common/Card';
import { useAuthStore } from '../../store/authStore';
import { useExercises } from '../../hooks/useExercises';

export const HomeScreen: React.FC = () => {
  const user = useAuthStore((s) => s.user);
  const { exercises, loading, fetch } = useExercises();
  const navigation = useNavigation<any>();

  useEffect(() => {
    fetch();
  }, []);

  const quickActions = [
    {
      icon: '📹',
      label: 'Analyze Video',
      description: 'Check your form against a reference',
      onPress: () => navigation.navigate('Analyze'),
    },
    {
      icon: '🏋️',
      label: 'Manage Exercises',
      description: 'View and add exercise references',
      onPress: () => navigation.navigate('Exercises'),
    },
  ];

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Hello, {user?.username ?? 'there'} 👋</Text>
          <Text style={styles.subtitle}>Ready to analyze your workout?</Text>
        </View>

        <Card style={styles.statsCard}>
          <Text style={styles.statsValue}>{loading ? '—' : exercises.length}</Text>
          <Text style={styles.statsLabel}>Exercise References</Text>
          {exercises.length === 0 && !loading && (
            <Text style={styles.statsHint}>Record a reference video to get started</Text>
          )}
        </Card>

        <Text style={styles.sectionTitle}>Quick Actions</Text>

        {quickActions.map((action) => (
          <TouchableOpacity key={action.label} onPress={action.onPress} activeOpacity={0.8}>
            <Card style={styles.actionCard}>
              <Text style={styles.actionIcon}>{action.icon}</Text>
              <View style={styles.actionContent}>
                <Text style={styles.actionLabel}>{action.label}</Text>
                <Text style={styles.actionDescription}>{action.description}</Text>
              </View>
              <Text style={styles.chevron}>›</Text>
            </Card>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  scroll: { padding: SPACING.lg, gap: SPACING.md },
  header: { marginBottom: SPACING.sm },
  greeting: { color: COLORS.text, fontSize: FONT_SIZE.xxl, fontWeight: '700', marginBottom: 4 },
  subtitle: { color: COLORS.textSecondary, fontSize: FONT_SIZE.md },
  statsCard: { alignItems: 'center', paddingVertical: SPACING.xl },
  statsValue: { color: COLORS.primary, fontSize: 56, fontWeight: '700', lineHeight: 64 },
  statsLabel: { color: COLORS.textSecondary, fontSize: FONT_SIZE.md, marginTop: 4 },
  statsHint: { color: COLORS.textMuted, fontSize: FONT_SIZE.sm, marginTop: SPACING.xs },
  sectionTitle: { color: COLORS.text, fontSize: FONT_SIZE.lg, fontWeight: '600' },
  actionCard: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  actionIcon: { fontSize: 32 },
  actionContent: { flex: 1 },
  actionLabel: { color: COLORS.text, fontSize: FONT_SIZE.md, fontWeight: '600' },
  actionDescription: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginTop: 2 },
  chevron: { color: COLORS.textMuted, fontSize: 24 },
});
