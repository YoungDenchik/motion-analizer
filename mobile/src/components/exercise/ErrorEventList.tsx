import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, FONT_SIZE, SPACING, SEVERITY_COLORS } from '../../constants';
import { StatusBadge } from '../common/StatusBadge';
import type { ErrorEvent } from '../../types/api';

const FEATURE_LABELS: Record<string, string> = {
  left_knee_angle: 'Left Knee',
  right_knee_angle: 'Right Knee',
  left_hip_angle: 'Left Hip',
  right_hip_angle: 'Right Hip',
  left_elbow_angle: 'Left Elbow',
  right_elbow_angle: 'Right Elbow',
  left_shoulder_angle: 'Left Shoulder',
  right_shoulder_angle: 'Right Shoulder',
  torso_lean: 'Torso Lean',
};

interface ErrorEventListProps {
  events: ErrorEvent[];
}

export const ErrorEventList: React.FC<ErrorEventListProps> = ({ events }) => {
  if (events.length === 0) {
    return <Text style={styles.empty}>No significant errors detected.</Text>;
  }

  return (
    <View style={styles.container}>
      {events.map((event, i) => {
        const severityColor = SEVERITY_COLORS[event.severity] ?? COLORS.textSecondary;
        const label = FEATURE_LABELS[event.feature_name] ?? event.feature_name;
        const directionText = event.direction === 'above' ? 'too much' : 'too little';

        return (
          <View key={i} style={styles.row}>
            <View style={styles.header}>
              <Text style={styles.joint}>{label}</Text>
              <StatusBadge label={event.severity} color={severityColor} />
            </View>
            <Text style={styles.detail}>
              {directionText} · avg {event.mean_deviation_deg.toFixed(1)}° off ·{' '}
              {Math.round(event.affected_frame_ratio * 100)}% of frames
            </Text>
          </View>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { gap: SPACING.sm },
  row: {
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  joint: { color: COLORS.text, fontSize: FONT_SIZE.md, fontWeight: '600' },
  detail: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm },
  empty: {
    color: COLORS.textSecondary,
    fontSize: FONT_SIZE.sm,
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: SPACING.sm,
  },
});
