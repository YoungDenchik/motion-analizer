import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps, NavigatorScreenParams } from '@react-navigation/native';
import type { AnalysisResult, HistoryEntry } from './api';

export type AuthStackParamList = {
  ServerConfig: undefined;
  Login: undefined;
  Register: undefined;
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

export type HistoryStackParamList = {
  HistoryList: undefined;
  HistoryDetail: { entry: HistoryEntry };
};

export type MainTabParamList = {
  Home: undefined;
  Exercises: NavigatorScreenParams<ExercisesStackParamList>;
  Analyze: NavigatorScreenParams<AnalyzeStackParamList>;
  History: NavigatorScreenParams<HistoryStackParamList>;
  Settings: undefined;
};

export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
};

export type ServerConfigScreenProps = NativeStackScreenProps<AuthStackParamList, 'ServerConfig'>;
export type LoginScreenProps = NativeStackScreenProps<AuthStackParamList, 'Login'>;
export type RegisterScreenProps = NativeStackScreenProps<AuthStackParamList, 'Register'>;

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

export type HistoryScreenProps = CompositeScreenProps<
  NativeStackScreenProps<HistoryStackParamList, 'HistoryList'>,
  BottomTabScreenProps<MainTabParamList>
>;
export type HistoryDetailScreenProps = NativeStackScreenProps<HistoryStackParamList, 'HistoryDetail'>;
