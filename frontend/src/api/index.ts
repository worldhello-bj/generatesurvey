import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
  timeout: 60000,
});

// Attach JWT token if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Questionnaire ──────────────────────────────────────────────────────────

export interface Question {
  id: string;
  text: string;
  type: 'single_choice' | 'multiple_choice' | 'rating' | 'open_ended';
  options: string[];
  required: boolean;
}

export interface Questionnaire {
  title: string;
  questions: Question[];
}

export const parseQuestionnaire = async (
  file?: File,
  text?: string
): Promise<{ task_id: string; questionnaire: Questionnaire }> => {
  const form = new FormData();
  if (file) form.append('file', file);
  if (text) form.append('text', text);
  const res = await api.post('/questionnaire/parse', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// ── Generation ─────────────────────────────────────────────────────────────

export interface StartRequest {
  task_id: string;
  sample_count: number;
  demographics_config?: Record<string, unknown>;
  export_format?: 'csv' | 'excel';
}

export const startGeneration = async (body: StartRequest) => {
  const res = await api.post('/generate/start', body);
  return res.data;
};

export const getGenerationStatus = async (genTaskId: string) => {
  const res = await api.get(`/generate/status/${genTaskId}`);
  return res.data;
};

// ── Download ───────────────────────────────────────────────────────────────

export const getDownloadUrl = (token: string): string =>
  `${process.env.REACT_APP_API_BASE_URL || '/api'}/download/${token}`;

// ── Admin ──────────────────────────────────────────────────────────────────

export const adminLogin = async (username: string, password: string) => {
  const res = await api.post('/admin/login', { username, password });
  return res.data;
};

export const getAdminStats = async () => {
  const res = await api.get('/admin/stats');
  return res.data;
};

export const getCostTrend = async (days: number = 7) => {
  const res = await api.get('/admin/cost-trend', { params: { days } });
  return res.data;
};

export interface RecordsParams {
  page?: number;
  page_size?: number;
  task_type?: string;
  user_id?: string;
  model?: string;
}

export const getAdminRecords = async (params: RecordsParams = {}) => {
  const res = await api.get('/admin/records', { params });
  return res.data;
};

export default api;
