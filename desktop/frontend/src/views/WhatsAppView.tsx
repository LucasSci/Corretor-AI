import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { Section } from '../components/Section'
import { api } from '../lib/api'

function toQrSource(base64?: string) {
  if (!base64) return null
  return base64.startsWith('data:') ? base64 : `data:image/png;base64,${base64.includes(',') ? base64.split(',')[1] : base64}`
}

export function WhatsAppView() {
  const evolutionQuery = useQuery({
    queryKey: ['evolution-status'],
    queryFn: api.getEvolutionStatus,
    refetchInterval: 2000,
  })
  const settingsQuery = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [webhookUrl, setWebhookUrl] = useState('')
  const [testContact, setTestContact] = useState('21975907217')
  const [testMessage, setTestMessage] = useState('Teste operacional da desktop app.')

  const qrMutation = useMutation({ mutationFn: api.refreshQr })
  const webhookMutation = useMutation({
    mutationFn: api.configureWebhook,
    onSuccess: (payload) => setWebhookUrl(payload.url),
  })
  const chatMutation = useMutation({
    mutationFn: () => api.sendChatTest(testContact, testMessage, `${testContact}@s.whatsapp.net`),
  })

  const qrSource = useMemo(() => toQrSource(qrMutation.data?.raw?.base64 as string | undefined), [qrMutation.data])
  const effectiveWebhook = webhookUrl || settingsQuery.data?.evolution.webhookUrl || evolutionQuery.data?.webhook_url || ''

  return (
    <div className="view-stack">
      <div className="two-column-grid two-column-grid-wide">
        <Section eyebrow="WhatsApp" title="Instancia e conexao" actions={<button className="ghost-button" onClick={() => qrMutation.mutate()}>Gerar QR</button>}>
          <div className="info-grid compact-grid">
            <div>
              <span>Instancia</span>
              <strong>{evolutionQuery.data?.instance ?? '...'}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{evolutionQuery.data?.status ?? '...'}</strong>
            </div>
            <div>
              <span>Reachability</span>
              <strong>{evolutionQuery.data?.reachable ? 'Online' : 'Offline'}</strong>
            </div>
            <div>
              <span>Numero autorizado</span>
              <strong>{settingsQuery.data?.operator.allowedNumbers || 'nao configurado'}</strong>
            </div>
          </div>

          <label className="field-block">
            <span>Webhook local</span>
            <input value={effectiveWebhook} onChange={(event) => setWebhookUrl(event.target.value)} />
          </label>

          <div className="button-row">
            <button onClick={() => webhookMutation.mutate(effectiveWebhook)}>Reconfigurar webhook</button>
            <button className="ghost-button" onClick={() => evolutionQuery.refetch()}>Atualizar status</button>
          </div>
          {webhookMutation.data ? <p className="helper-text">Webhook ajustado para {webhookMutation.data.url}</p> : null}
        </Section>

        <Section eyebrow="Pareamento" title="QR e fallback de conexao">
          {qrSource ? (
            <img className="qr-frame" src={qrSource} alt="QR Code da Evolution" />
          ) : (
            <div className="placeholder-surface">
              <strong>Nenhum QR gerado nesta sessao.</strong>
              <p>Use o botao “Gerar QR” para solicitar um novo pareamento da instância.</p>
            </div>
          )}
          {qrMutation.data?.pairing_code ? <p className="helper-text">Pairing code: {qrMutation.data.pairing_code}</p> : null}
        </Section>
      </div>

      <Section eyebrow="Teste" title="Envio rapido de mensagem">
        <div className="inline-form">
          <label className="field-block">
            <span>Numero</span>
            <input value={testContact} onChange={(event) => setTestContact(event.target.value)} />
          </label>
          <label className="field-block field-grow">
            <span>Mensagem</span>
            <input value={testMessage} onChange={(event) => setTestMessage(event.target.value)} />
          </label>
          <button onClick={() => chatMutation.mutate()}>Disparar teste</button>
        </div>
        {chatMutation.data ? <p className="helper-text">Resultado: {chatMutation.data.ok ? 'enviado' : 'falhou'}</p> : null}
      </Section>
    </div>
  )
}
