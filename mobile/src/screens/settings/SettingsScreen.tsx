import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet, ScrollView, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { useAuthStore } from '../../store/authStore';

export const SettingsScreen: React.FC = () => {
  const { serverUrl, user, setServerUrl, logout } = useAuthStore();
  const [urlDraft, setUrlDraft] = useState(serverUrl);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const clean = urlDraft.replace(/\/+$/, '').trim();
    if (!clean) {
      Alert.alert('Missing URL', 'Server URL is required.');
      return;
    }
    setSaving(true);
    await setServerUrl(clean);
    setSaving(false);
    Alert.alert('Saved', 'Server URL updated.');
  };

  const handleLogout = () => {
    Alert.alert('Sign Out', 'You will be signed out of your account.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: logout },
    ]);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Card>
          <Text style={styles.cardTitle}>Account</Text>
          <View style={styles.row}>
            <Text style={styles.label}>Username</Text>
            <Text style={styles.value}>{user?.username ?? '—'}</Text>
          </View>
          <View style={styles.row}>
            <Text style={styles.label}>Email</Text>
            <Text style={styles.value}>{user?.email ?? '—'}</Text>
          </View>
        </Card>

        <Card>
          <Text style={styles.cardTitle}>Connection</Text>
          <Text style={styles.label}>Server URL</Text>
          <TextInput
            style={styles.input}
            value={urlDraft}
            onChangeText={setUrlDraft}
            placeholder="http://192.168.1.x:8000"
            placeholderTextColor={COLORS.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />
          <Button label="Save URL" onPress={handleSave} loading={saving} />
        </Card>

        <Card style={styles.aboutCard}>
          <Text style={styles.cardTitle}>About</Text>
          <Text style={styles.aboutLine}>AI Fitness Coach — Mobile v1.0.0</Text>
          <Text style={styles.aboutLine}>Backend: FastAPI + MediaPipe + DTW</Text>
          <Text style={styles.aboutLine}>Built with Expo + React Native</Text>
        </Card>

        <Button label="Sign Out" onPress={handleLogout} variant="danger" />
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  scroll: { padding: SPACING.lg, gap: SPACING.md },
  cardTitle: { color: COLORS.text, fontSize: FONT_SIZE.md, fontWeight: '700', marginBottom: SPACING.md },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACING.sm },
  label: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm },
  value: { color: COLORS.text, fontSize: FONT_SIZE.sm, fontWeight: '500' },
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
    marginTop: 4,
  },
  aboutCard: {},
  aboutLine: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginBottom: 4 },
});
