import type { PropsWithChildren, ReactNode } from 'react'

export function Section({
  eyebrow,
  title,
  actions,
  children,
}: PropsWithChildren<{ eyebrow: string; title: string; actions?: ReactNode }>) {
  return (
    <section className="panel-section">
      <header className="section-head">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </header>
      {children}
    </section>
  )
}
