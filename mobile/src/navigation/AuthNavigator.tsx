import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ServerConfigScreen } from '../screens/auth/ServerConfigScreen';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { RegisterScreen } from '../screens/auth/RegisterScreen';
import { useAuthStore } from '../store/authStore';
import type { AuthStackParamList } from '../types/navigation';
import { COLORS, FONT_SIZE } from '../constants';

const Stack = createNativeStackNavigator<AuthStackParamList>();

export const AuthNavigator: React.FC = () => {
  const serverUrl = useAuthStore((s) => s.serverUrl);

  return (
    <Stack.Navigator
      initialRouteName={serverUrl ? 'Login' : 'ServerConfig'}
      screenOptions={{
        headerStyle: { backgroundColor: COLORS.surface },
        headerTintColor: COLORS.text,
        headerTitleStyle: { fontWeight: '600' as const, fontSize: FONT_SIZE.lg },
        headerShadowVisible: false,
        contentStyle: { backgroundColor: COLORS.background },
      }}
    >
      <Stack.Screen
        name="ServerConfig"
        component={ServerConfigScreen}
        options={{ title: 'Server Setup', headerShown: false }}
      />
      <Stack.Screen
        name="Login"
        component={LoginScreen}
        options={{ title: 'Sign In', headerShown: false }}
      />
      <Stack.Screen
        name="Register"
        component={RegisterScreen}
        options={{ title: 'Create Account', headerBackTitle: 'Sign In' }}
      />
    </Stack.Navigator>
  );
};
