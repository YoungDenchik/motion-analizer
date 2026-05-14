import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SetupScreen } from '../screens/auth/SetupScreen';
import type { AuthStackParamList } from '../types/navigation';
import { COLORS } from '../constants';

const Stack = createNativeStackNavigator<AuthStackParamList>();

export const AuthNavigator: React.FC = () => (
  <Stack.Navigator
    screenOptions={{ headerShown: false, contentStyle: { backgroundColor: COLORS.background } }}
  >
    <Stack.Screen name="Setup" component={SetupScreen} />
  </Stack.Navigator>
);
