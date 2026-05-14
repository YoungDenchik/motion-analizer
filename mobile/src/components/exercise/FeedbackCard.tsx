import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, FONT_SIZE, SPACING, SEVERITY_COLORS } from '../../constants';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';
import type { FeedbackItem } from '../../types/api';

interface FeedbackCardProps {
  item: FeedbackItem;
  index: number;
}

export const FeedbackCard: React.FC<FeedbackCardProps> = ({ item, index }) => {
  const severityColor = SEVERITY_COLORS[item.severity] ?? COLORS.textSecondary;

  return (
    <Card style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.index}>#{index + 1}</Text>
        <StatusBadge label={item.severity} color={severityColor} />
        <Text style={styles.deviation}>±{item.mean_deviation_deg.toFixed(1)}°</Text>
      </View>
      <Text style={styles.cue}>{item.cue}</Text>
      <Text style={styles.explanation}>{item.explanation}</Text>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { marginBottom: SPACING.sm },
  header: { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm, marginBottom: SPACING.sm },
  index: { color: COLORS.textMuted, fontSize: FONT_SIZE.sm, fontWeight: '600' },
  deviation: { color: COLORS.textSecondary, fontSize: FONT_SIZE.xs, marginLeft: 'auto' },
  cue: { color: COLORS.text, fontSize: FONT_SIZE.md, fontWeight: '600', marginBottom: SPACING.xs, lineHeight: 22 },
  explanation: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, lineHeight: 20 },
});
