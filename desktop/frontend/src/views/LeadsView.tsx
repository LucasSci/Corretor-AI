import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Section } from '../components/Section'
import { api } from '../lib/api'

export function LeadsView() {
  const [selectedContact, setSelectedContact] = useState<string | undefined>(undefined)
  const leadsQuery = useQuery({
    queryKey: ['leads'],
    queryFn: api.getLeads,
    refetchInterval: 2500,
  })
  const messagesQuery = useQuery({
    queryKey: ['messages', selectedContact],
    queryFn: () => api.getMessages(selectedContact),
    refetchInterval: 2000,
  })

  return (
    <div className="two-column-grid two-column-grid-wide">
      <Section eyebrow="Pipeline" title="Leads qualificados e em progresso">
        <div className="table-list selectable-list">
          {(leadsQuery.data?.items ?? []).map((lead) => (
            <button className="table-row table-button" key={lead.id} onClick={() => setSelectedContact(lead.contact_id)}>
              <div>
                <strong>{lead.contact_id}</strong>
                <p>{String(lead.profile.nome ?? lead.profile.bairro ?? 'perfil em construcao')}</p>
              </div>
              <div className="table-meta">
                <span>{lead.stage}</span>
              </div>
            </button>
          ))}
        </div>
      </Section>

      <Section eyebrow="Historico" title="Mensagens persistidas">
        <div className="table-list">
          {(messagesQuery.data?.items ?? []).map((message) => (
            <div className="table-row" key={message.id}>
              <div>
                <strong>{message.direction}</strong>
                <p>{message.text}</p>
              </div>
              <div className="table-meta">
                <span>{message.status}</span>
                <span>{message.contact_id ?? message.remote_jid ?? 'sistema'}</span>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
