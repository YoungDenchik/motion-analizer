import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Button } from '../../components/common/Button';
import { Card } from '../../components/common/Card';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { useExercises } from '../../hooks/useExercises';
import { useAnalysis } from '../../hooks/useAnalysis';
import type { AnalyzeSelectScreenProps } from '../../types/navigation';

export const AnalyzeScreen: React.FC<AnalyzeSelectScreenProps> = ({ navigation }) => {
  const { exercises, loading: exercisesLoading, fetch } = useExercises();
  const { phase, uploadProgress, jobId, error, startAnalysis } = useAnalysis();
  const [selectedExercise, setSelectedExercise] = useState<string | null>(null);
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [videoName, setVideoName] = useState<string | null>(null);

  useEffect(() => {
    fetch();
  }, []);

  useEffect(() => {
    if (exercises.length > 0 && !selectedExercise) {
      setSelectedExercise(exercises[0]);
    }
  }, [exercises]);

  useEffect(() => {
    if (phase === 'processing' && jobId && selectedExercise) {
      navigation.navigate('JobPolling', { jobId, exercise: selectedExercise });
    }
  }, [phase, jobId]);

  const pickVideo = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Required', 'Please allow access to your photo library.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Videos,
      quality: 1,
    });
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      setVideoUri(asset.uri);
      setVideoName(asset.fileName ?? `video_${Date.now()}.mp4`);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedExercise || !videoUri || !videoName) return;
    await startAnalysis(selectedExercise, videoUri, videoName);
  };

  if (exercisesLoading) {
    return <LoadingSpinner message="Loading exercises…" />;
  }

  if (exercises.length === 0) {
    return (
      <SafeAreaView style={styles.safe} edges={['bottom']}>
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>🏋️</Text>
          <Text style={styles.emptyTitle}>No References Yet</Text>
          <Text style={styles.emptySubtitle}>
            Go to Exercises and record a reference video before you can analyze your form.
          </Text>
          <Button
            label="Go to Exercises"
            onPress={() => navigation.navigate('Exercises' as any)}
            variant="outline"
            style={{ marginTop: SPACING.lg }}
          />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {error && <ErrorMessage message={error} />}

          <Text style={styles.label}>Select Exercise</Text>
          <View style={styles.pillGrid}>
            {exercises.map((ex) => (
              <TouchableOpacity
                key={ex}
                onPress={() => setSelectedExercise(ex)}
                style={[styles.pill, selectedExercise === ex && styles.pillSelected]}
                activeOpacity={0.7}
              >
                <Text style={[styles.pillText, selectedExercise === ex && styles.pillTextSelected]}>
                  {ex}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.label}>Your Video</Text>
          <Button
            label={videoUri ? '✓ Video selected — tap to change' : 'Select Video from Library'}
            onPress={pickVideo}
            variant={videoUri ? 'secondary' : 'outline'}
          />

          {phase === 'uploading' && (
            <Card style={styles.progressCard}>
              <Text style={styles.progressText}>Uploading… {uploadProgress}%</Text>
              <View style={styles.progressBg}>
                <View style={[styles.progressFill, { width: `${uploadProgress}%` }]} />
              </View>
            </Card>
          )}

          <Button
            label="Analyze My Form"
            onPress={handleAnalyze}
            loading={phase === 'uploading'}
            disabled={!selectedExercise || !videoUri}
            style={styles.analyzeBtn}
          />

          <Text style={styles.tip}>
            💡 Make sure your full body is visible and record from a side view for best results.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  flex: { flex: 1 },
  scroll: { padding: SPACING.lg, gap: SPACING.md },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: SPACING.xl,
    gap: SPACING.sm,
  },
  emptyIcon: { fontSize: 56 },
  emptyTitle: { color: COLORS.text, fontSize: FONT_SIZE.xl, fontWeight: '700' },
  emptySubtitle: {
    color: COLORS.textSecondary,
    fontSize: FONT_SIZE.md,
    textAlign: 'center',
    lineHeight: 22,
  },
  label: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginBottom: 4 },
  pillGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.sm },
  pill: {
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderRadius: BORDER_RADIUS.full,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  pillSelected: { backgroundColor: `${COLORS.primary}25`, borderColor: COLORS.primary },
  pillText: {
    color: COLORS.textSecondary,
    fontSize: FONT_SIZE.sm,
    fontWeight: '500',
    textTransform: 'capitalize',
  },
  pillTextSelected: { color: COLORS.primary },
  progressCard: {},
  progressText: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginBottom: SPACING.xs },
  progressBg: { height: 6, backgroundColor: COLORS.surfaceLight, borderRadius: BORDER_RADIUS.full },
  progressFill: { height: '100%', backgroundColor: COLORS.primary, borderRadius: BORDER_RADIUS.full },
  analyzeBtn: {},
  tip: { color: COLORS.textMuted, fontSize: FONT_SIZE.xs, lineHeight: 18, textAlign: 'center' },
});
