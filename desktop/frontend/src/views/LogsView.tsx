import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Section } from '../components/Section'
import { api } from '../lib/api'

export function LogsView() {
  const [source, setSource] = useState<'combined' | 'stdout' | 'stderr'>('combined')
  const logsQuery = useQuery({
    queryKey: ['logs', source],
    queryFn: () => api.getLogs(source),
    refetchInterval: 1500,
  })

  return (
    <div className="view-stack">
      <Section eyebrow="Observabilidade" title="Tail dos logs do backend" actions={<span className="status-pill">{source}</span>}>
        <div className="button-row">
          <button className={source === 'combined' ? 'ghost-button active' : 'ghost-button'} onClick={() => setSource('combined')}>Combinado</button>
          <button className={source === 'stdout' ? 'ghost-button active' : 'ghost-button'} onClick={() => setSource('stdout')}>Stdout</button>
          <button className={source === 'stderr' ? 'ghost-button active' : 'ghost-button'} onClick={() => setSource('stderr')}>Stderr</button>
        </div>
        <div className="logs-grid">
          <div className="log-surface">
            {(logsQuery.data?.stdout ?? []).map((line, index) => (
              <div key={`out-${index}`}>{line}</div>
            ))}
          </div>
          <div className="log-surface danger-surface">
            {(logsQuery.data?.stderr ?? []).map((line, index) => (
              <div key={`err-${index}`}>{line}</div>
            ))}
          </div>
        </div>
      </Section>
    </div>
  )
}
