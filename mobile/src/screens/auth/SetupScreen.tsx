import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Button } from '../../components/common/Button';
import { useAuthStore } from '../../store/authStore';
import { api } from '../../api/endpoints';
import type { SetupScreenProps } from '../../types/navigation';

export const SetupScreen: React.FC<SetupScreenProps> = () => {
  const [serverUrl, setServerUrl] = useState('http://');
  const [userName, setUserName] = useState('');
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);

  const handleConnect = async () => {
    const cleanUrl = serverUrl.replace(/\/+$/, '').trim();
    if (!cleanUrl || cleanUrl === 'http://' || cleanUrl === 'https://') {
      Alert.alert('Missing URL', 'Please enter your server address.');
      return;
    }
    if (!userName.trim()) {
      Alert.alert('Missing Name', 'Please enter your name.');
      return;
    }

    setLoading(true);
    const ok = await api.testConnectivity(cleanUrl);
    setLoading(false);

    if (!ok) {
      Alert.alert(
        'Cannot Connect',
        `Could not reach the server at:\n${cleanUrl}\n\nMake sure:\n• Your iPhone and computer are on the same Wi-Fi\n• The backend is running\n• The IP address and port are correct`
      );
      return;
    }

    await login(cleanUrl, userName.trim());
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.hero}>
            <Text style={styles.emoji}>🏋️</Text>
            <Text style={styles.title}>AI Fitness Coach</Text>
            <Text style={styles.subtitle}>Analyze your exercise form with AI</Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.sectionTitle}>Connect to Your Server</Text>
            <Text style={styles.hint}>
              Run{' '}
              <Text style={styles.code}>ipconfig</Text>
              {' '}on Windows to find your computer's local IP, then enter it below.
            </Text>

            <Text style={styles.label}>Server URL</Text>
            <TextInput
              style={styles.input}
              value={serverUrl}
              onChangeText={setServerUrl}
              placeholder="http://192.168.1.x:80"
              placeholderTextColor={COLORS.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              returnKeyType="next"
            />

            <Text style={styles.label}>Your Name</Text>
            <TextInput
              style={styles.input}
              value={userName}
              onChangeText={setUserName}
              placeholder="Alex"
              placeholderTextColor={COLORS.textMuted}
              autoCorrect={false}
              returnKeyType="done"
              onSubmitEditing={handleConnect}
            />

            <Button label="Connect" onPress={handleConnect} loading={loading} style={styles.button} />
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
  sectionTitle: { color: COLORS.text, fontSize: FONT_SIZE.lg, fontWeight: '600', marginBottom: SPACING.xs },
  hint: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, lineHeight: 20, marginBottom: SPACING.sm },
  code: { color: COLORS.primary, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  label: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginTop: SPACING.xs, marginBottom: 4 },
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
  button: { marginTop: SPACING.md },
});
