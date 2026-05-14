import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';

import { HomeScreen } from '../screens/home/HomeScreen';
import { ExercisesScreen } from '../screens/exercises/ExercisesScreen';
import { RecordReferenceScreen } from '../screens/exercises/RecordReferenceScreen';
import { AnalyzeScreen } from '../screens/analyze/AnalyzeScreen';
import { JobPollingScreen } from '../screens/analyze/JobPollingScreen';
import { ResultScreen } from '../screens/analyze/ResultScreen';
import { SettingsScreen } from '../screens/settings/SettingsScreen';

import type {
  MainTabParamList,
  ExercisesStackParamList,
  AnalyzeStackParamList,
} from '../types/navigation';
import { COLORS, FONT_SIZE, SPACING } from '../constants';

const Tab = createBottomTabNavigator<MainTabParamList>();
const ExercisesStack = createNativeStackNavigator<ExercisesStackParamList>();
const AnalyzeStack = createNativeStackNavigator<AnalyzeStackParamList>();

const stackScreenOptions = {
  headerStyle: { backgroundColor: COLORS.surface },
  headerTintColor: COLORS.text,
  headerTitleStyle: { fontWeight: '600' as const, fontSize: FONT_SIZE.lg },
  contentStyle: { backgroundColor: COLORS.background },
  headerShadowVisible: false,
};

const ExercisesNavigator: React.FC = () => (
  <ExercisesStack.Navigator screenOptions={stackScreenOptions}>
    <ExercisesStack.Screen
      name="ExercisesList"
      component={ExercisesScreen}
      options={{ title: 'Exercises' }}
    />
    <ExercisesStack.Screen
      name="RecordReference"
      component={RecordReferenceScreen}
      options={{ title: 'Record Reference' }}
    />
  </ExercisesStack.Navigator>
);

const AnalyzeNavigator: React.FC = () => (
  <AnalyzeStack.Navigator screenOptions={stackScreenOptions}>
    <AnalyzeStack.Screen
      name="AnalyzeSelect"
      component={AnalyzeScreen}
      options={{ title: 'Analyze' }}
    />
    <AnalyzeStack.Screen
      name="JobPolling"
      component={JobPollingScreen}
      options={{ title: 'Processing…', headerBackVisible: false }}
    />
    <AnalyzeStack.Screen
      name="Result"
      component={ResultScreen}
      options={{ title: 'Your Results' }}
    />
  </AnalyzeStack.Navigator>
);

const TAB_ICONS: Record<string, [string, string]> = {
  Home: ['home', 'home-outline'],
  Exercises: ['barbell', 'barbell-outline'],
  Analyze: ['analytics', 'analytics-outline'],
  Settings: ['settings', 'settings-outline'],
};

export const MainNavigator: React.FC = () => (
  <Tab.Navigator
    screenOptions={({ route }) => ({
      tabBarIcon: ({ focused, color, size }) => {
        const [active, inactive] = TAB_ICONS[route.name] ?? ['ellipse', 'ellipse-outline'];
        return (
          <Ionicons name={(focused ? active : inactive) as any} size={size} color={color} />
        );
      },
      tabBarActiveTintColor: COLORS.primary,
      tabBarInactiveTintColor: COLORS.textMuted,
      tabBarStyle: {
        backgroundColor: COLORS.surface,
        borderTopColor: COLORS.border,
        borderTopWidth: 1,
        paddingBottom: SPACING.xs,
        height: 60,
      },
      tabBarLabelStyle: { fontSize: FONT_SIZE.xs },
      headerShown: false,
    })}
  >
    <Tab.Screen name="Home" component={HomeScreen} />
    <Tab.Screen name="Exercises" component={ExercisesNavigator} />
    <Tab.Screen name="Analyze" component={AnalyzeNavigator} />
    <Tab.Screen name="Settings" component={SettingsScreen} />
  </Tab.Navigator>
);
