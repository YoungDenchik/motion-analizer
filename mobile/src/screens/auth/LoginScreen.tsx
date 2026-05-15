import React, { useState, useRef } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Button } from '../../components/common/Button';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { useAuthStore } from '../../store/authStore';
import { api } from '../../api/endpoints';
import type { LoginScreenProps } from '../../types/navigation';

export const LoginScreen: React.FC<LoginScreenProps> = ({ navigation }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const passwordRef = useRef<TextInput>(null);
  const { loginSuccess, serverUrl, setServerUrl } = useAuthStore();

  const handleLogin = async () => {
    if (!email.trim() || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.auth.login({ email: email.trim(), password });
      await loginSuccess(res.access_token, res.user);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.hero}>
            <Text style={styles.emoji}>🏋️</Text>
            <Text style={styles.title}>Welcome back</Text>
            <Text style={styles.subtitle}>{serverUrl}</Text>
          </View>

          {error && <ErrorMessage message={error} />}

          <Text style={styles.label}>Email</Text>
          <TextInput
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
            placeholderTextColor={COLORS.textMuted}
            autoCapitalize="none"
            keyboardType="email-address"
            returnKeyType="next"
            onSubmitEditing={() => passwordRef.current?.focus()}
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            ref={passwordRef}
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            placeholderTextColor={COLORS.textMuted}
            secureTextEntry
            returnKeyType="done"
            onSubmitEditing={handleLogin}
          />

          <Button label="Sign In" onPress={handleLogin} loading={loading} style={styles.btn} />

          <View style={styles.footer}>
            <Text style={styles.footerText}>Don't have an account? </Text>
            <TouchableOpacity onPress={() => navigation.navigate('Register')}>
              <Text style={styles.link}>Create one</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={styles.changeServer}
            onPress={() => {
              setServerUrl('');
              navigation.replace('ServerConfig');
            }}
          >
            <Text style={styles.changeServerText}>Change server</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, padding: SPACING.lg },
  hero: { alignItems: 'center', paddingVertical: SPACING.xl, marginBottom: SPACING.sm },
  emoji: { fontSize: 56, marginBottom: SPACING.sm },
  title: { color: COLORS.text, fontSize: FONT_SIZE.xxl, fontWeight: '700' },
  subtitle: { color: COLORS.textMuted, fontSize: FONT_SIZE.xs, marginTop: 4 },
  label: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, marginBottom: 4, marginTop: SPACING.sm },
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
  btn: { marginTop: SPACING.lg },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: SPACING.lg },
  footerText: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm },
  link: { color: COLORS.primary, fontSize: FONT_SIZE.sm, fontWeight: '600' },
  changeServer: { alignItems: 'center', marginTop: SPACING.xl },
  changeServerText: { color: COLORS.textMuted, fontSize: FONT_SIZE.xs },
});
