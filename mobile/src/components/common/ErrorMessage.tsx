import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, FONT_SIZE, SPACING, BORDER_RADIUS } from '../../constants';

interface ErrorMessageProps {
  message: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message }) => (
  <View style={styles.container}>
    <Text style={styles.icon}>⚠</Text>
    <Text style={styles.text}>{message}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    backgroundColor: `${COLORS.error}20`,
    borderWidth: 1,
    borderColor: `${COLORS.error}55`,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: SPACING.sm,
  },
  icon: { color: COLORS.error, fontSize: FONT_SIZE.lg },
  text: { color: COLORS.error, fontSize: FONT_SIZE.sm, flex: 1, lineHeight: 20 },
});
