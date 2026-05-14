import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { COLORS, SPACING, FONT_SIZE } from '../../constants';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Button } from '../../components/common/Button';
import { useJobPoller } from '../../hooks/useJobPoller';
import type { JobPollingScreenProps } from '../../types/navigation';

const PROGRESS_MESSAGES = [
  'Detecting pose landmarks…',
  'Extracting joint angles…',
  'Segmenting repetitions…',
  'Running DTW comparison…',
  'Scoring your form…',
  'Generating feedback…',
  'Rendering annotated video…',
  'Almost done…',
];

export const JobPollingScreen: React.FC<JobPollingScreenProps> = ({ navigation, route }) => {
  const { jobId, exercise } = route.params;
  const { status, result, error, attempts } = useJobPoller(jobId);

  useEffect(() => {
    if (status === 'done' && result) {
      navigation.replace('Result', { result, jobId });
    }
  }, [status, result]);

  if (status === 'error') {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.container}>
          <Text style={styles.bigIcon}>❌</Text>
          <Text style={styles.title}>Analysis Failed</Text>
          <ErrorMessage message={error ?? 'Unknown error'} />
          <Button label="Go Back" onPress={() => navigation.goBack()} style={styles.btn} />
        </View>
      </SafeAreaView>
    );
  }

  const msgIndex = Math.min(Math.floor(attempts / 5), PROGRESS_MESSAGES.length - 1);
  const dotPhase = attempts % 3;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.bigIcon}>🤖</Text>
        <Text style={styles.title}>Analyzing your {exercise}</Text>
        <Text style={styles.progressMsg}>{PROGRESS_MESSAGES[msgIndex]}</Text>
        <Text style={styles.hint}>This may take 1–2 minutes</Text>
        <View style={styles.dots}>
          {[0, 1, 2].map((i) => (
            <View key={i} style={[styles.dot, { opacity: dotPhase === i ? 1 : 0.25 }]} />
          ))}
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: SPACING.xl,
    gap: SPACING.md,
  },
  bigIcon: { fontSize: 72, marginBottom: SPACING.sm },
  title: {
    color: COLORS.text,
    fontSize: FONT_SIZE.xl,
    fontWeight: '700',
    textAlign: 'center',
    textTransform: 'capitalize',
  },
  progressMsg: { color: COLORS.primary, fontSize: FONT_SIZE.md, textAlign: 'center' },
  hint: { color: COLORS.textMuted, fontSize: FONT_SIZE.sm },
  dots: { flexDirection: 'row', gap: SPACING.sm, marginTop: SPACING.sm },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: COLORS.primary },
  btn: { marginTop: SPACING.lg, width: '100%' },
});
