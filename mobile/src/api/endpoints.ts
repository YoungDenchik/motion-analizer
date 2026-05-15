import { apiClient, uploadClient } from './client';
import type {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  ReferencesListResponse,
  RecordResponse,
  AnalyzeResponse,
  DeleteResponse,
  JobResponse,
  AnalysisResult,
  ReferenceResult,
  User,
} from '../types/api';

function makeVideoFormData(
  videoUri: string,
  videoName: string,
  extra: Record<string, string>
): FormData {
  const form = new FormData();
  Object.entries(extra).forEach(([k, v]) => form.append(k, v));
  form.append('video', { uri: videoUri, name: videoName, type: 'video/mp4' } as unknown as Blob);
  return form;
}

export const api = {
  auth: {
    async register(req: RegisterRequest): Promise<AuthResponse> {
      const { data } = await apiClient.post<AuthResponse>('/auth/register', req);
      return data;
    },
    async login(req: LoginRequest): Promise<AuthResponse> {
      const { data } = await apiClient.post<AuthResponse>('/auth/login', req);
      return data;
    },
    async me(): Promise<User> {
      const { data } = await apiClient.get<User>('/auth/me');
      return data;
    },
  },

  references: {
    async list(): Promise<ReferencesListResponse> {
      const { data } = await apiClient.get<ReferencesListResponse>('/references');
      return data;
    },

    async record(
      name: string,
      videoUri: string,
      videoName: string,
      description?: string,
      overwrite = false,
      onUploadProgress?: (pct: number) => void
    ): Promise<RecordResponse> {
      const extra: Record<string, string> = { name, overwrite: String(overwrite) };
      if (description) extra.description = description;
      const form = makeVideoFormData(videoUri, videoName, extra);
      const { data } = await uploadClient.post<RecordResponse>('/references/record', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (onUploadProgress && e.total) {
            onUploadProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      });
      return data;
    },

    async delete(name: string): Promise<DeleteResponse> {
      const { data } = await apiClient.delete<DeleteResponse>(
        `/references/${encodeURIComponent(name)}`
      );
      return data;
    },
  },

  analysis: {
    async start(
      exercise: string,
      videoUri: string,
      videoName: string,
      onUploadProgress?: (pct: number) => void
    ): Promise<AnalyzeResponse> {
      const form = makeVideoFormData(videoUri, videoName, { exercise });
      const { data } = await uploadClient.post<AnalyzeResponse>('/analyze', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (onUploadProgress && e.total) {
            onUploadProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      });
      return data;
    },

    async getStatus(jobId: string): Promise<JobResponse<AnalysisResult>> {
      const { data } = await apiClient.get<JobResponse<AnalysisResult>>(`/status/${jobId}`);
      return data;
    },

    async getReferenceStatus(jobId: string): Promise<JobResponse<ReferenceResult>> {
      const { data } = await apiClient.get<JobResponse<ReferenceResult>>(`/status/${jobId}`);
      return data;
    },
  },

  async testConnectivity(serverUrl: string): Promise<boolean> {
    try {
      await apiClient.get('/auth/me', { baseURL: `${serverUrl}/api` });
      return true;
    } catch (e: any) {
      // 401 means the server is reachable (auth required) — that's fine
      return e?.message?.includes('401') || e?.response?.status === 401
        || String(e).includes('Invalid or expired');
    }
  },
};

export function getVideoUrl(serverUrl: string, jobId: string): string {
  return `${serverUrl}/api/video/${jobId}`;
}
