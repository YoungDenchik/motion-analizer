import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, FONT_SIZE, SPACING, BORDER_RADIUS, GRADE_COLORS } from '../../constants';

interface RepScoreListProps {
  scores: number[];
  bestIndex: number;
  worstIndex: number;
}

function scoreToGrade(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

export const RepScoreList: React.FC<RepScoreListProps> = ({ scores, bestIndex, worstIndex }) => (
  <View style={styles.container}>
    {scores.map((score, i) => {
      const grade = scoreToGrade(score);
      const color = GRADE_COLORS[grade] ?? COLORS.textSecondary;
      const isBest = i === bestIndex;
      const isWorst = i === worstIndex && scores.length > 1;

      return (
        <View key={i} style={styles.row}>
          <View style={styles.labelCol}>
            <Text style={styles.repNum}>Rep {i + 1}</Text>
            {isBest && <Text style={[styles.tag, { color: GRADE_COLORS.A }]}>BEST</Text>}
            {isWorst && <Text style={[styles.tag, { color: COLORS.error }]}>WORST</Text>}
          </View>
          <View style={styles.barBg}>
            <View style={[styles.barFill, { width: `${score}%`, backgroundColor: color }]} />
          </View>
          <Text style={[styles.scoreNum, { color }]}>{Math.round(score)}</Text>
        </View>
      );
    })}
  </View>
);

const styles = StyleSheet.create({
  container: { gap: SPACING.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  labelCol: { width: 70, flexDirection: 'row', alignItems: 'center', gap: 4 },
  repNum: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm },
  tag: { fontSize: 9, fontWeight: '700', letterSpacing: 0.3 },
  barBg: {
    flex: 1,
    height: 8,
    backgroundColor: COLORS.surfaceLight,
    borderRadius: BORDER_RADIUS.full,
    overflow: 'hidden',
  },
  barFill: { height: '100%', borderRadius: BORDER_RADIUS.full },
  scoreNum: { width: 32, textAlign: 'right', fontSize: FONT_SIZE.sm, fontWeight: '600' },
});
