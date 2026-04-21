import { useQuery } from '@tanstack/react-query'

import { Section } from '../components/Section'
import { api } from '../lib/api'

function formatTimestamp(value?: string | null): string {
  if (!value) return 'sem registro'
  return new Date(value).toLocaleString('pt-BR')
}

function StatBand({ label, value, tone = 'default' }: { label: string; value: string | number; tone?: 'default' | 'accent' }) {
  return (
    <article className={`stat-band ${tone === 'accent' ? 'stat-band-accent' : ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  )
}

export function DashboardView() {
  const statusQuery = useQuery({
    queryKey: ['admin-status'],
    queryFn: api.getStatus,
    refetchInterval: 2000,
  })

  const data = statusQuery.data

  return (
    <div className="view-stack">
      <section className="hero-strip">
        <div>
          <p className="eyebrow">Operacao local</p>
          <h1>Suite do corretor em tempo real.</h1>
          <p className="hero-copy">
            Monitoramos saude do backend, Evolution, jobs de ingestao, uploads e historico operacional no mesmo plano.
          </p>
        </div>
        <div className="hero-status">
          <span className={`status-pill ${data?.backend.healthy ? 'status-ok' : 'status-warn'}`}>
            {statusQuery.isFetching ? 'Sincronizando' : data?.backend.healthy ? 'Backend online' : 'Backend indisponivel'}
          </span>
          <span className={`status-pill ${data?.evolution.reachable ? 'status-ok' : 'status-danger'}`}>
            {data?.evolution.status ?? 'Sem dados da Evolution'}
          </span>
        </div>
      </section>

      <div className="stats-grid">
        <StatBand label="Leads" value={data?.counts.leads.total ?? '...'} tone="accent" />
        <StatBand label="Mensagens" value={data?.counts.messages.total ?? '...'} />
        <StatBand label="Uploads" value={data?.counts.uploads ?? '...'} />
        <StatBand label="Porta local" value={data?.backend.port ?? '...'} />
      </div>

      <div className="two-column-grid">
        <Section eyebrow="Recente" title="Atividade operacional">
          <div className="table-list">
            {(data?.recent_activity ?? []).map((item) => (
              <div className="table-row" key={item.id}>
                <div>
                  <strong>{item.contact_id ?? item.remote_jid ?? 'sistema'}</strong>
                  <p>{item.text || '[sem texto]'}</p>
                </div>
                <div className="table-meta">
                  <span>{item.status}</span>
                  <span>{formatTimestamp(item.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section eyebrow="Jobs" title="Ingestao e tarefas longas">
          <div className="table-list">
            {(data?.recent_jobs ?? []).map((job) => (
              <div className="table-row" key={job.id}>
                <div>
                  <strong>{job.kind}</strong>
                  <p>{job.message}</p>
                </div>
                <div className="table-meta">
                  <span>{job.status}</span>
                  <span>{Math.round(job.progress)}%</span>
                </div>
              </div>
            ))}
          </div>
        </Section>
      </div>

      <Section eyebrow="Arquivos" title="Uploads recentes">
        <div className="table-list">
          {(data?.uploads ?? []).map((item) => (
            <div className="table-row" key={item.path}>
              <div>
                <strong>{item.name}</strong>
                <p>{item.path}</p>
              </div>
              <div className="table-meta">
                <span>{item.type}</span>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
