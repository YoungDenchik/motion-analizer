import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps, NavigatorScreenParams } from '@react-navigation/native';
import type { AnalysisResult } from './api';

export type AuthStackParamList = {
  Setup: undefined;
};

export type ExercisesStackParamList = {
  ExercisesList: undefined;
  RecordReference: undefined;
};

export type AnalyzeStackParamList = {
  AnalyzeSelect: undefined;
  JobPolling: { jobId: string; exercise: string };
  Result: { result: AnalysisResult; jobId: string };
};

export type MainTabParamList = {
  Home: undefined;
  Exercises: NavigatorScreenParams<ExercisesStackParamList>;
  Analyze: NavigatorScreenParams<AnalyzeStackParamList>;
  Settings: undefined;
};

export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
};

export type SetupScreenProps = NativeStackScreenProps<AuthStackParamList, 'Setup'>;

export type ExercisesListScreenProps = CompositeScreenProps<
  NativeStackScreenProps<ExercisesStackParamList, 'ExercisesList'>,
  BottomTabScreenProps<MainTabParamList>
>;

export type RecordReferenceScreenProps = NativeStackScreenProps<ExercisesStackParamList, 'RecordReference'>;

export type AnalyzeSelectScreenProps = CompositeScreenProps<
  NativeStackScreenProps<AnalyzeStackParamList, 'AnalyzeSelect'>,
  BottomTabScreenProps<MainTabParamList>
>;

export type JobPollingScreenProps = NativeStackScreenProps<AnalyzeStackParamList, 'JobPolling'>;

export type ResultScreenProps = NativeStackScreenProps<AnalyzeStackParamList, 'Result'>;
