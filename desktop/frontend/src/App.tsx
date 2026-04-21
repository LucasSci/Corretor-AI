import { useEffect, useMemo, useState } from 'react'

import { ensureSidecarStarted } from './lib/desktopRuntime'
import { getApiBaseUrl } from './lib/api'
import { DashboardView } from './views/DashboardView'
import { IngestionView } from './views/IngestionView'
import { LeadsView } from './views/LeadsView'
import { LogsView } from './views/LogsView'
import { SettingsView } from './views/SettingsView'
import { WhatsAppView } from './views/WhatsAppView'
import './App.css'

type ViewKey = 'dashboard' | 'whatsapp' | 'leads' | 'ingestion' | 'settings' | 'logs'

const NAV_ITEMS: Array<{ key: ViewKey; label: string; hint: string }> = [
  { key: 'dashboard', label: 'Dashboard', hint: 'Status, contagem e jobs' },
  { key: 'whatsapp', label: 'WhatsApp', hint: 'QR, webhook e testes' },
  { key: 'leads', label: 'Leads', hint: 'Perfil e historico persistido' },
  { key: 'ingestion', label: 'Ingestao', hint: 'RAG, documentos e linktree' },
  { key: 'settings', label: 'Settings', hint: 'Credenciais e rede local' },
  { key: 'logs', label: 'Logs', hint: 'stdout e stderr do backend' },
]

function readInitialView(): ViewKey {
  if (typeof window === 'undefined') return 'dashboard'
  const stored = window.localStorage.getItem('corretoria.desktop.activeView') as ViewKey | null
  return stored ?? 'dashboard'
}

function CurrentView({ activeView }: { activeView: ViewKey }) {
  switch (activeView) {
    case 'whatsapp':
      return <WhatsAppView />
    case 'leads':
      return <LeadsView />
    case 'ingestion':
      return <IngestionView />
    case 'settings':
      return <SettingsView />
    case 'logs':
      return <LogsView />
    case 'dashboard':
    default:
      return <DashboardView />
  }
}

function App() {
  const [activeView, setActiveView] = useState<ViewKey>(readInitialView)
  const [runtimeState, setRuntimeState] = useState<{ started: boolean; mode: string; error?: string }>({
    started: false,
    mode: 'booting',
  })

  const apiBaseUrl = useMemo(() => getApiBaseUrl(), [])

  useEffect(() => {
    window.localStorage.setItem('corretoria.desktop.activeView', activeView)
  }, [activeView])

  useEffect(() => {
    let mounted = true
    ensureSidecarStarted(apiBaseUrl).then((state) => {
      if (mounted) {
        setRuntimeState(state)
      }
    })
    return () => {
      mounted = false
    }
  }, [apiBaseUrl])

  return (
    <div className="desktop-shell">
      <aside className="rail">
        <div className="brand-block">
          <p className="brand-kicker">CorretorIA</p>
          <h1>Desktop operativo para WhatsApp e RAG.</h1>
          <p>
            Base local, webhook Evolution, ingestao de conhecimento e observabilidade do atendimento em um fluxo unico.
          </p>
        </div>

        <nav className="rail-nav" aria-label="Navegacao principal">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`rail-link ${activeView === item.key ? 'rail-link-active' : ''}`}
              onClick={() => setActiveView(item.key)}
            >
              <strong>{item.label}</strong>
              <span>{item.hint}</span>
            </button>
          ))}
        </nav>

        <div className="runtime-block">
          <span className={`status-pill ${runtimeState.started ? 'status-ok' : runtimeState.mode === 'error' ? 'status-danger' : 'status-warn'}`}>
            {runtimeState.started ? `Sidecar ${runtimeState.mode}` : `Runtime ${runtimeState.mode}`}
          </span>
          <p>{apiBaseUrl}</p>
          {runtimeState.error ? <p className="runtime-error">{runtimeState.error}</p> : null}
        </div>
      </aside>

      <main className="workspace">
        <CurrentView activeView={activeView} />
      </main>
    </div>
  )
}

export default App
