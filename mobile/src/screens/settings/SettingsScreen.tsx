import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, ScrollView, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { useAuthStore } from '../../store/authStore';

export const SettingsScreen: React.FC = () => {
  const { serverUrl, userName, updateServerUrl, updateUserName, logout } = useAuthStore();
  const [urlDraft, setUrlDraft] = useState(serverUrl);
  const [nameDraft, setNameDraft] = useState(userName);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!urlDraft.trim() || !nameDraft.trim()) {
      Alert.alert('Missing Fields', 'Both server URL and name are required.');
      return;
    }
    setSaving(true);
    await Promise.all([
      updateServerUrl(urlDraft.replace(/\/+$/, '').trim()),
      updateUserName(nameDraft.trim()),
    ]);
    setSaving(false);
    Alert.alert('Saved', 'Settings updated successfully.');
  };

  const handleLogout = () => {
    Alert.alert('Disconnect', 'This will clear your saved server and profile. Continue?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Disconnect', style: 'destructive', onPress: logout },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Card>
          <Text style={styles.cardTitle}>Connection</Text>

          <Text style={styles.label}>Server URL</Text>
          <TextInput
            style={styles.input}
            value={urlDraft}
            onChangeText={setUrlDraft}
            placeholder="http://192.168.1.x:80"
            placeholderTextColor={COLORS.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />

          <Text style={styles.label}>Your Name</Text>
          <TextInput
            style={styles.input}
            value={nameDraft}
            onChangeText={setNameDraft}
            placeholder="Your name"
            placeholderTextColor={COLORS.textMuted}
          />

          <Button label="Save Changes" onPress={handleSave} loading={saving} />
        </Card>

        <Card style={styles.aboutCard}>
          <Text style={styles.cardTitle}>About</Text>
          <Text style={styles.aboutLine}>AI Fitness Coach — Mobile v1.0.0</Text>
          <Text style={styles.aboutLine}>Backend: FastAPI + MediaPipe + DTW</Text>
          <Text style={styles.aboutLine}>Built with Expo + React Native</Text>
        </Card>

        <Button label="Disconnect" onPress={handleLogout} variant="danger" />
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  scroll: { padding: SPACING.lg, gap: SPACING.md },
  cardTitle: { color: COLORS.text, fontSize: FONT_SIZE.md, fontWeight: '700', marginBottom: SPACING.md },
  label: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginBottom: 4 },
  input: {
    backgroundColor: COLORS.surfaceLight,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: BORDER_RADIUS.md,
    color: COLORS.text,
    fontSize: FONT_SIZE.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: 14,
    marginBottom: SPACING.md,
  },
  aboutCard: {},
  aboutLine: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginBottom: 4 },
});
