import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Button } from '../../components/common/Button';
import { useAuthStore } from '../../store/authStore';
import { api } from '../../api/endpoints';
import type { ServerConfigScreenProps } from '../../types/navigation';

export const ServerConfigScreen: React.FC<ServerConfigScreenProps> = ({ navigation }) => {
  const [serverUrl, setServerUrl] = useState('http://');
  const [loading, setLoading] = useState(false);
  const setServerUrlStore = useAuthStore((s) => s.setServerUrl);

  const handleContinue = async () => {
    const cleanUrl = serverUrl.replace(/\/+$/, '').trim();
    if (!cleanUrl || cleanUrl === 'http://' || cleanUrl === 'https://') {
      Alert.alert('Missing URL', 'Please enter your server address.');
      return;
    }
    setLoading(true);
    const ok = await api.testConnectivity(cleanUrl);
    setLoading(false);
    if (!ok) {
      Alert.alert(
        'Cannot Connect',
        `Could not reach:\n${cleanUrl}\n\nMake sure:\n• Phone and computer are on the same Wi-Fi\n• The backend is running\n• The IP and port are correct`
      );
      return;
    }
    await setServerUrlStore(cleanUrl);
    navigation.replace('Login');
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.hero}>
            <Text style={styles.emoji}>🏋️</Text>
            <Text style={styles.title}>AI Fitness Coach</Text>
            <Text style={styles.subtitle}>Connect to your backend server</Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.hint}>
              Run <Text style={styles.code}>ipconfig</Text> on Windows to find your
              computer's local IP, then enter it below.
            </Text>
            <Text style={styles.label}>Server URL</Text>
            <TextInput
              style={styles.input}
              value={serverUrl}
              onChangeText={setServerUrl}
              placeholder="http://192.168.1.x:8000"
              placeholderTextColor={COLORS.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              returnKeyType="done"
              onSubmitEditing={handleContinue}
            />
            <Button label="Continue" onPress={handleContinue} loading={loading} style={styles.btn} />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, padding: SPACING.lg },
  hero: { alignItems: 'center', paddingVertical: SPACING.xxl },
  emoji: { fontSize: 72, marginBottom: SPACING.md },
  title: { color: COLORS.text, fontSize: FONT_SIZE.xxl, fontWeight: '700', marginBottom: SPACING.xs },
  subtitle: { color: COLORS.textSecondary, fontSize: FONT_SIZE.md },
  form: { gap: SPACING.sm },
  hint: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, lineHeight: 20 },
  code: { color: COLORS.primary, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  label: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginTop: SPACING.sm },
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
  btn: { marginTop: SPACING.md },
});
