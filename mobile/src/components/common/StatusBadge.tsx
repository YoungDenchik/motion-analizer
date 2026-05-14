import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { FONT_SIZE, SPACING, BORDER_RADIUS } from '../../constants';

interface StatusBadgeProps {
  label: string;
  color: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ label, color }) => (
  <View style={[styles.badge, { backgroundColor: `${color}25`, borderColor: `${color}60` }]}>
    <Text style={[styles.text, { color }]}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: 3,
    borderRadius: BORDER_RADIUS.full,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: FONT_SIZE.xs,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});
