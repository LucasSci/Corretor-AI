import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { Section } from '../components/Section'
import { api } from '../lib/api'

export function IngestionView() {
  const [kind, setKind] = useState<'linktree_full' | 'manual_documents'>('linktree_full')
  const [sourcesText, setSourcesText] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)

  const createJobMutation = useMutation({
    mutationFn: () =>
      api.createIngestionJob(
        kind,
        sourcesText
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean),
      ),
    onSuccess: (job) => setJobId(job.id),
  })

  const jobQuery = useQuery({
    queryKey: ['ingestion-job', jobId],
    queryFn: () => api.getJob(jobId ?? ''),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ['completed', 'failed'].includes(status) ? false : 1000
    },
  })

  const activeJob = useMemo(() => jobQuery.data ?? createJobMutation.data, [jobQuery.data, createJobMutation.data])

  return (
    <div className="view-stack">
      <Section eyebrow="RAG" title="Ingestao operacional da base de conhecimento">
        <div className="inline-form stacked-mobile">
          <label className="field-block field-narrow">
            <span>Modo</span>
            <select value={kind} onChange={(event) => setKind(event.target.value as 'linktree_full' | 'manual_documents')}>
              <option value="linktree_full">Linktree completo</option>
              <option value="manual_documents">Documentos ou pastas locais</option>
            </select>
          </label>
          <button onClick={() => createJobMutation.mutate()}>Iniciar job</button>
        </div>

        <label className="field-block">
          <span>Fontes (uma por linha, opcional no modo linktree)</span>
          <textarea
            rows={6}
            value={sourcesText}
            onChange={(event) => setSourcesText(event.target.value)}
            placeholder={kind === 'manual_documents' ? 'C:\\Documentos\\cliente\\planta.pdf' : 'Deixe vazio para usar o pipeline atual'}
          />
        </label>
      </Section>

      <Section eyebrow="Execucao" title="Progresso do job atual">
        {activeJob ? (
          <>
            <div className="progress-rail">
              <div className="progress-fill" style={{ width: `${Math.round(activeJob.progress)}%` }} />
            </div>
            <div className="info-grid compact-grid">
              <div>
                <span>Status</span>
                <strong>{activeJob.status}</strong>
              </div>
              <div>
                <span>Mensagem</span>
                <strong>{activeJob.message || 'Aguardando atualizacao'}</strong>
              </div>
              <div>
                <span>Kind</span>
                <strong>{activeJob.kind}</strong>
              </div>
              <div>
                <span>Progresso</span>
                <strong>{Math.round(activeJob.progress)}%</strong>
              </div>
            </div>
            <div className="log-surface">
              {(activeJob.logs ?? []).map((line, index) => (
                <div key={`${activeJob.id}-${index}`}>{line}</div>
              ))}
            </div>
          </>
        ) : (
          <div className="placeholder-surface">
            <strong>Nenhum job disparado nesta sessao.</strong>
            <p>Assim que voce iniciar uma ingestao, o polling de progresso aparece aqui automaticamente.</p>
          </div>
        )}
      </Section>
    </div>
  )
}
