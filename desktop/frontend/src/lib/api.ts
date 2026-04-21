import type {
  AdminStatusResponse,
  EvolutionQrResponse,
  JobRun,
  LeadRecord,
  LogsResponse,
  MessageEvent,
  SettingsDocument,
  UploadEntry,
} from './types'

const API_BASE_STORAGE_KEY = 'corretoria.desktop.apiBaseUrl'
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export class ApiError extends Error {
  detail: unknown
  status: number

  constructor(message: string, status: number, detail: unknown) {
    super(message)
    this.detail = detail
    this.status = status
  }
}

export function getApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return DEFAULT_API_BASE_URL
  }
  return window.localStorage.getItem(API_BASE_STORAGE_KEY) ?? DEFAULT_API_BASE_URL
}

export function setApiBaseUrl(value: string): void {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(API_BASE_STORAGE_KEY, value)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let detail: unknown = null
    try {
      detail = await response.json()
    } catch {
      detail = await response.text()
    }
    throw new ApiError(`HTTP ${response.status}`, response.status, detail)
  }

  return (await response.json()) as T
}

export const api = {
  getStatus: () => request<AdminStatusResponse>('/admin/status'),
  getEvolutionStatus: () => request<AdminStatusResponse['evolution']>('/admin/evolution/status'),
  refreshQr: () => request<EvolutionQrResponse>('/admin/evolution/qr', { method: 'POST' }),
  configureWebhook: (url?: string) =>
    request<{ ok: boolean; instance: string; url: string }>('/admin/evolution/webhook', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),
  getSettings: () => request<SettingsDocument>('/admin/settings'),
  validateSettings: (payload: SettingsDocument) =>
    request<{ ok: boolean; warnings: string[]; restart_required_fields: string[] }>('/admin/settings/validate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  saveSettings: (payload: SettingsDocument) =>
    request<{ ok: boolean; warnings: string[]; restart_required_fields: string[]; path: string }>('/admin/settings', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createIngestionJob: (kind: string, sources: string[]) =>
    request<JobRun>('/admin/ingestion/jobs', {
      method: 'POST',
      body: JSON.stringify({ kind, sources }),
    }),
  getJob: (jobId: string) => request<JobRun>(`/admin/ingestion/jobs/${jobId}`),
  getUploads: () => request<{ items: UploadEntry[] }>('/admin/uploads'),
  getLeads: () => request<{ items: LeadRecord[] }>('/admin/leads'),
  getMessages: (contactId?: string) =>
    request<{ items: MessageEvent[] }>(`/admin/messages${contactId ? `?contact_id=${encodeURIComponent(contactId)}` : ''}`),
  getLogs: (source: 'combined' | 'stdout' | 'stderr') =>
    request<LogsResponse>(`/admin/logs/tail?source=${source}`),
  sendChatTest: (contactId: string, text: string, remoteJid?: string) =>
    request<{ ok: boolean; send_result: Record<string, unknown> }>('/admin/chat/test', {
      method: 'POST',
      body: JSON.stringify({ contact_id: contactId, text, remote_jid: remoteJid }),
    }),
}
