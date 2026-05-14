import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, FONT_SIZE, SPACING, BORDER_RADIUS, GRADE_COLORS } from '../../constants';

interface ScoreDisplayProps {
  score: number;
  grade: string;
  label?: string;
}

export const ScoreDisplay: React.FC<ScoreDisplayProps> = ({ score, grade, label }) => {
  const gradeColor = GRADE_COLORS[grade] ?? COLORS.textSecondary;

  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}
      <View style={styles.row}>
        <Text style={styles.score}>{Math.round(score)}</Text>
        <Text style={styles.unit}>/100</Text>
        <View style={[styles.grade, { backgroundColor: `${gradeColor}25`, borderColor: gradeColor }]}>
          <Text style={[styles.gradeText, { color: gradeColor }]}>{grade}</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { alignItems: 'center' },
  label: {
    color: COLORS.textSecondary,
    fontSize: FONT_SIZE.sm,
    marginBottom: SPACING.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: SPACING.sm },
  score: { color: COLORS.text, fontSize: FONT_SIZE.xxxl, fontWeight: '700', lineHeight: 44 },
  unit: { color: COLORS.textSecondary, fontSize: FONT_SIZE.lg, marginBottom: 6 },
  grade: {
    borderWidth: 2,
    borderRadius: BORDER_RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 4,
    marginBottom: 4,
  },
  gradeText: { fontSize: FONT_SIZE.xl, fontWeight: '700' },
});
