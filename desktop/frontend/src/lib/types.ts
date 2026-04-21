export type AdminStatusResponse = {
  backend: {
    app_name: string
    healthy: boolean
    host: string
    port: number
    settings_path: string
  }
  evolution: {
    reachable: boolean
    instance: string
    status: string
    base_url: string
    webhook_url: string
    error?: string
  }
  counts: {
    leads: { total: number }
    messages: { total: number; inbound: number; outbound: number }
    uploads: number
  }
  recent_jobs: JobRun[]
  recent_activity: MessageEvent[]
  uploads: UploadEntry[]
}

export type JobRun = {
  id: string
  kind: string
  status: string
  progress: number
  message: string
  payload: Record<string, unknown>
  result: Record<string, unknown>
  logs: string[]
  started_at?: string | null
  finished_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type MessageEvent = {
  id: number
  direction: string
  contact_id?: string | null
  remote_jid?: string | null
  text: string
  channel: string
  status: string
  meta: Record<string, unknown>
  created_at?: string | null
}

export type LeadRecord = {
  id: number
  contact_id: string
  stage: string
  profile: Record<string, unknown>
  created_at?: string | null
}

export type UploadEntry = {
  path: string
  name: string
  type: string
  modified_at: number
  metadata_path?: string | null
}

export type SettingsDocument = {
  llm: {
    provider: string
    modelName: string
    geminiApiKey: string
    openaiApiKey: string
    temperature: number
    chromaK: number
  }
  evolution: {
    baseUrl: string
    apiKey: string
    instance: string
    webhookUrl: string
  }
  storage: {
    dbUrl: string
    uploadsDir: string
    mediaAutoSave: boolean
  }
  network: {
    host: string
    port: number
    corsOrigins: string[]
  }
  operator: {
    allowedNumbers: string
    commandNumbers: string
    testNumber: string
    botNumber: string
    allowFromMeTest: boolean
    loopGuardTtlSec: number
  }
}

export type LogsResponse = {
  stdout: string[]
  stderr: string[]
}

export type EvolutionQrResponse = {
  ok: boolean
  instance: string
  qr_path?: string | null
  pairing_code?: string | null
  has_qr: boolean
  raw?: {
    base64?: string
    pairingCode?: string
    [key: string]: unknown
  }
}
