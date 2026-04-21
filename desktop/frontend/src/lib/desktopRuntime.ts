const SIDECAR_SETTINGS_PATH = 'data/desktop_settings.json'

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown
  }
}

let sidecarStarted = false
let sidecarPromise: Promise<{ started: boolean; mode: string; error?: string }> | null = null

function isTauriEnvironment(): boolean {
  return typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__)
}

async function probeHealth(baseUrl: string, retries = 12, waitMs = 500): Promise<boolean> {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      const response = await fetch(`${baseUrl}/health`)
      if (response.ok) {
        return true
      }
    } catch {
      // keep polling
    }
    await new Promise((resolve) => window.setTimeout(resolve, waitMs))
  }
  return false
}

export async function ensureSidecarStarted(baseUrl: string): Promise<{ started: boolean; mode: string; error?: string }> {
  if (!isTauriEnvironment()) {
    return { started: false, mode: 'browser' }
  }

  if (sidecarStarted) {
    return { started: true, mode: 'sidecar' }
  }

  if (sidecarPromise) {
    return sidecarPromise
  }

  sidecarPromise = (async () => {
    const target = new URL(baseUrl)
    try {
      const { Command } = await import('@tauri-apps/plugin-shell')
      const command = Command.sidecar('binaries/corretor-backend', [
        '--host',
        target.hostname,
        '--port',
        target.port || '8000',
        '--settings-path',
        SIDECAR_SETTINGS_PATH,
      ])
      await command.spawn()
      const healthy = await probeHealth(baseUrl, 18, 600)
      if (!healthy) {
        return { started: false, mode: 'error', error: 'Backend local nao respondeu apos o spawn do sidecar.' }
      }
      sidecarStarted = true
      return { started: true, mode: 'sidecar' }
    } catch (error) {
      const healthy = await probeHealth(baseUrl, 4, 400)
      if (healthy) {
        sidecarStarted = true
        return { started: true, mode: 'existing', error: String(error) }
      }
      return { started: false, mode: 'error', error: String(error) }
    }
  })()

  return sidecarPromise
}
