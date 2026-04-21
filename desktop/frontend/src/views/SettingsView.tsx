import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import { Section } from '../components/Section'
import { api, setApiBaseUrl } from '../lib/api'
import type { SettingsDocument } from '../lib/types'

function toListValue(values: string[]) {
  return values.join(', ')
}

export function SettingsView() {
  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [draft, setDraft] = useState<SettingsDocument | null>(null)

  useEffect(() => {
    if (settingsQuery.data) {
      setDraft(settingsQuery.data)
    }
  }, [settingsQuery.data])

  const validateMutation = useMutation({ mutationFn: (payload: SettingsDocument) => api.validateSettings(payload) })
  const saveMutation = useMutation({
    mutationFn: (payload: SettingsDocument) => api.saveSettings(payload),
    onSuccess: (_, payload) => setApiBaseUrl(`http://127.0.0.1:${payload.network.port}`),
  })

  const helpers = useMemo(() => validateMutation.data ?? saveMutation.data, [saveMutation.data, validateMutation.data])

  if (!draft) {
    return <div className="placeholder-surface">Carregando configuracoes...</div>
  }

  return (
    <div className="view-stack">
      <Section eyebrow="Credenciais" title="Configuracao local da operacao">
        <div className="settings-grid">
          <label className="field-block">
            <span>Modelo Gemini</span>
            <input value={draft.llm.modelName} onChange={(event) => setDraft({ ...draft, llm: { ...draft.llm, modelName: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Gemini API Key</span>
            <input value={draft.llm.geminiApiKey} onChange={(event) => setDraft({ ...draft, llm: { ...draft.llm, geminiApiKey: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>OpenAI API Key</span>
            <input value={draft.llm.openaiApiKey} onChange={(event) => setDraft({ ...draft, llm: { ...draft.llm, openaiApiKey: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Evolution URL</span>
            <input value={draft.evolution.baseUrl} onChange={(event) => setDraft({ ...draft, evolution: { ...draft.evolution, baseUrl: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Evolution API Key</span>
            <input value={draft.evolution.apiKey} onChange={(event) => setDraft({ ...draft, evolution: { ...draft.evolution, apiKey: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Instancia</span>
            <input value={draft.evolution.instance} onChange={(event) => setDraft({ ...draft, evolution: { ...draft.evolution, instance: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Webhook URL</span>
            <input value={draft.evolution.webhookUrl} onChange={(event) => setDraft({ ...draft, evolution: { ...draft.evolution, webhookUrl: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Uploads Dir</span>
            <input value={draft.storage.uploadsDir} onChange={(event) => setDraft({ ...draft, storage: { ...draft.storage, uploadsDir: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Porta local</span>
            <input type="number" value={draft.network.port} onChange={(event) => setDraft({ ...draft, network: { ...draft.network, port: Number(event.target.value) } })} />
          </label>
          <label className="field-block">
            <span>Host local</span>
            <input value={draft.network.host} onChange={(event) => setDraft({ ...draft, network: { ...draft.network, host: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Allowed numbers</span>
            <input value={draft.operator.allowedNumbers} onChange={(event) => setDraft({ ...draft, operator: { ...draft.operator, allowedNumbers: event.target.value } })} />
          </label>
          <label className="field-block">
            <span>Command numbers</span>
            <input value={draft.operator.commandNumbers} onChange={(event) => setDraft({ ...draft, operator: { ...draft.operator, commandNumbers: event.target.value } })} />
          </label>
        </div>

        <label className="field-block">
          <span>CORS Origins</span>
          <input
            value={toListValue(draft.network.corsOrigins)}
            onChange={(event) =>
              setDraft({
                ...draft,
                network: {
                  ...draft.network,
                  corsOrigins: event.target.value
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean),
                },
              })
            }
          />
        </label>

        <div className="button-row">
          <button onClick={() => validateMutation.mutate(draft)}>Validar</button>
          <button className="ghost-button" onClick={() => saveMutation.mutate(draft)}>Salvar</button>
        </div>
        {helpers?.warnings?.length ? <p className="helper-text">Avisos: {helpers.warnings.join(' | ')}</p> : null}
        {helpers?.restart_required_fields?.length ? <p className="helper-text">Campos que exigem restart do sidecar: {helpers.restart_required_fields.join(', ')}</p> : null}
      </Section>
    </div>
  )
}
