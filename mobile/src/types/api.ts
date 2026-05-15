export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface FeedbackItem {
  cue: string;
  explanation: string;
  severity: 'critical' | 'technical';
  feature: string;
  mean_deviation_deg: number;
}

export interface FeedbackReport {
  grade_message: string;
  summary: string;
  items: FeedbackItem[];
}

export interface ErrorEvent {
  feature_name: string;
  severity: 'critical' | 'technical';
  direction: 'above' | 'below';
  mean_deviation_deg: number;
  max_deviation_deg: number;
  affected_frame_ratio: number;
  start_frame: number;
  end_frame: number;
}

export interface AnalysisResult {
  exercise_name: string;
  overall_score: number;
  grade: string;
  duration_seconds: number;
  frame_count: number;
  detected_frame_count: number;
  num_reps: number;
  per_rep_scores: number[];
  score_consistency: number;
  best_rep_index: number;
  worst_rep_index: number;
  dtw_distance: number;
  normalized_dtw_distance: number;
  has_annotated_video: boolean;
  render_error: string | null;
  processing_time_seconds: number;
  error_events: ErrorEvent[];
  feedback: FeedbackReport;
}

export interface ReferenceResult {
  name: string;
  description?: string;
  num_frames: number;
  fps: number;
}

export type JobStatus = 'pending' | 'done' | 'error';

export interface JobResponse<T> {
  status: JobStatus;
  result?: T;
  error?: string;
}

export interface ReferencesListResponse {
  exercises: string[];
}

export interface RecordResponse {
  job_id: string;
}

export interface AnalyzeResponse {
  job_id: string;
}

export interface DeleteResponse {
  success: boolean;
}

export interface HistoryEntry {
  id: string;
  exercise: string;
  date: string;
  result: AnalysisResult;
}
