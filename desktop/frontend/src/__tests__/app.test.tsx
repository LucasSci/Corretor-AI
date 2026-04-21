import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import App from '../App'

function buildFetchMock() {
  const job = {
    id: 'job-1',
    kind: 'linktree_full',
    status: 'running',
    progress: 60,
    message: 'Executando',
    payload: {},
    result: {},
    logs: ['inicio', 'processando'],
  }

  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/admin/status')) {
      return new Response(JSON.stringify({ backend: { app_name: 'CorretorIA', healthy: true, host: '0.0.0.0', port: 8000, settings_path: 'data/desktop_settings.json' }, evolution: { reachable: true, instance: 'BotRiva', status: 'open', base_url: 'http://127.0.0.1:8080', webhook_url: 'http://host.docker.internal:8000/webhook' }, counts: { leads: { total: 4 }, messages: { total: 8, inbound: 4, outbound: 4 }, uploads: 2 }, recent_jobs: [job], recent_activity: [{ id: 1, direction: 'inbound', contact_id: '21975907217', remote_jid: '21975907217@s.whatsapp.net', text: 'oi', channel: 'whatsapp', status: 'processed', meta: {} }], uploads: [{ path: 'C:/tmp/file.pdf', name: 'file.pdf', type: 'document', modified_at: Date.now() }] }))
    }
    if (url.endsWith('/admin/settings')) {
      return new Response(JSON.stringify({ llm: { provider: 'gemini', modelName: 'gemini-2.5-flash', geminiApiKey: 'abc', openaiApiKey: '', temperature: 0.6, chromaK: 4 }, evolution: { baseUrl: 'http://127.0.0.1:8080', apiKey: 'token', instance: 'BotRiva', webhookUrl: 'http://host.docker.internal:8000/webhook' }, storage: { dbUrl: 'sqlite+aiosqlite:///./data/app.db', uploadsDir: 'data/whatsapp_uploads', mediaAutoSave: true }, network: { host: '0.0.0.0', port: 8000, corsOrigins: ['http://127.0.0.1:1420'] }, operator: { allowedNumbers: '21975907217', commandNumbers: '21975907217', testNumber: '', botNumber: '', allowFromMeTest: true, loopGuardTtlSec: 30 } }))
    }
    if (url.endsWith('/admin/evolution/status')) {
      return new Response(JSON.stringify({ reachable: true, instance: 'BotRiva', status: 'open', base_url: 'http://127.0.0.1:8080', webhook_url: 'http://host.docker.internal:8000/webhook' }))
    }
    if (url.endsWith('/admin/leads')) {
      return new Response(JSON.stringify({ items: [{ id: 1, contact_id: '21975907217', stage: 'qualificando', profile: { bairro: 'Recreio' } }] }))
    }
    if (url.startsWith('http://127.0.0.1:8000/admin/messages')) {
      return new Response(JSON.stringify({ items: [{ id: 1, direction: 'inbound', contact_id: '21975907217', text: 'quero saber mais', channel: 'whatsapp', status: 'processed', meta: {} }] }))
    }
    if (url.includes('/admin/ingestion/jobs/job-1')) {
      return new Response(JSON.stringify(job))
    }
    if (url.endsWith('/admin/ingestion/jobs') && init?.method === 'POST') {
      return new Response(JSON.stringify(job))
    }
    if (url.endsWith('/admin/settings/validate') && init?.method === 'POST') {
      return new Response(JSON.stringify({ ok: true, warnings: ['validacao mock'], restart_required_fields: ['network.port'] }))
    }
    if (url.endsWith('/health')) {
      return new Response(JSON.stringify({ ok: true }))
    }
    if (url.endsWith('/admin/logs/tail?source=combined')) {
      return new Response(JSON.stringify({ stdout: ['ok'], stderr: [] }))
    }
    return new Response(JSON.stringify({ ok: true }))
  })
}

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><App /></QueryClientProvider>)
}

describe('desktop frontend', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', buildFetchMock())
    window.localStorage.clear()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders dashboard metrics from the admin API', async () => {
    renderApp()
    await waitFor(() => expect(screen.getByText('Suite do corretor em tempo real.')).toBeInTheDocument())
    expect(screen.getAllByText('Leads').length).toBeGreaterThan(0)
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('validates the settings form through the backend API', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getAllByRole('button', { name: /Settings.*Credenciais e rede local/i })[0])
    await waitFor(() => expect(screen.getByText('Configuracao local da operacao')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Validar' }))
    await waitFor(() => expect(screen.getByText(/validacao mock/i)).toBeInTheDocument())
  })

  it('creates and shows an ingestion job', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getAllByRole('button', { name: /Ingestao.*RAG, documentos e linktree/i })[0])
    await waitFor(() => expect(screen.getByText('Ingestao operacional da base de conhecimento')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Iniciar job' }))
    await waitFor(() => expect(screen.getByText('Executando')).toBeInTheDocument())
    expect(screen.getByText('60%')).toBeInTheDocument()
  })
})
