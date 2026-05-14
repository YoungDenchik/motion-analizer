import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ScrollView,
  Switch,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Button } from '../../components/common/Button';
import { Card } from '../../components/common/Card';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { api } from '../../api/endpoints';
import type { RecordReferenceScreenProps } from '../../types/navigation';

export const RecordReferenceScreen: React.FC<RecordReferenceScreenProps> = ({ navigation }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [overwrite, setOverwrite] = useState(false);
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [videoName, setVideoName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const pickVideo = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Required', 'Please allow access to your photo library to select a video.');
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

  const handleSubmit = async () => {
    if (!name.trim()) {
      Alert.alert('Missing Name', 'Please enter an exercise name.');
      return;
    }
    if (!videoUri || !videoName) {
      Alert.alert('No Video', 'Please select a video file.');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      await api.references.record(
        name.trim().toLowerCase(),
        videoUri,
        videoName,
        description.trim() || undefined,
        overwrite,
        setUploadProgress
      );
      Alert.alert(
        'Upload Complete',
        'Your reference video is being processed. This may take a minute.',
        [{ text: 'OK', onPress: () => navigation.goBack() }]
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {error && <ErrorMessage message={error} />}

          <Text style={styles.label}>Exercise Name *</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="squat, deadlift, pushup…"
            placeholderTextColor={COLORS.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="next"
          />

          <Text style={styles.label}>Description (optional)</Text>
          <TextInput
            style={styles.input}
            value={description}
            onChangeText={setDescription}
            placeholder="Side view squat reference"
            placeholderTextColor={COLORS.textMuted}
            returnKeyType="done"
          />

          <View style={styles.toggleRow}>
            <View style={styles.toggleLabels}>
              <Text style={styles.toggleTitle}>Overwrite if exists</Text>
              <Text style={styles.toggleSub}>Replace an existing reference with this name</Text>
            </View>
            <Switch
              value={overwrite}
              onValueChange={setOverwrite}
              trackColor={{ false: COLORS.border, true: COLORS.primary }}
              thumbColor={COLORS.text}
            />
          </View>

          <Text style={styles.label}>Reference Video *</Text>
          <Button
            label={videoUri ? '✓ Video selected — tap to change' : 'Select Video from Library'}
            onPress={pickVideo}
            variant={videoUri ? 'secondary' : 'outline'}
          />

          {uploading && (
            <Card style={styles.progressCard}>
              <Text style={styles.progressText}>Uploading… {uploadProgress}%</Text>
              <View style={styles.progressBg}>
                <View style={[styles.progressFill, { width: `${uploadProgress}%` }]} />
              </View>
            </Card>
          )}

          <Button
            label="Upload & Record"
            onPress={handleSubmit}
            loading={uploading}
            disabled={!name.trim() || !videoUri}
            style={styles.submitBtn}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  flex: { flex: 1 },
  scroll: { padding: SPACING.lg, gap: SPACING.sm },
  label: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginTop: SPACING.xs },
  input: {
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: BORDER_RADIUS.md,
    color: COLORS.text,
    fontSize: FONT_SIZE.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: 14,
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: COLORS.surface,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    borderWidth: 1,
    borderColor: COLORS.border,
    marginTop: SPACING.xs,
  },
  toggleLabels: { flex: 1, marginRight: SPACING.md },
  toggleTitle: { color: COLORS.text, fontSize: FONT_SIZE.md, fontWeight: '500' },
  toggleSub: { color: COLORS.textSecondary, fontSize: FONT_SIZE.xs, marginTop: 2 },
  progressCard: { marginTop: SPACING.sm },
  progressText: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginBottom: SPACING.xs },
  progressBg: { height: 6, backgroundColor: COLORS.surfaceLight, borderRadius: BORDER_RADIUS.full },
  progressFill: { height: '100%', backgroundColor: COLORS.primary, borderRadius: BORDER_RADIUS.full },
  submitBtn: { marginTop: SPACING.lg },
});
