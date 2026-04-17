import type { PropsWithChildren, ReactNode } from "react";

type Props = PropsWithChildren<{
  title: string;
  actions?: ReactNode;
  className?: string;
}>;

export function SectionCard({ title, actions, className, children }: Props) {
  return (
    <section className={`card ${className ?? ""}`.trim()}>
      <div className="card-header">
        <h2>{title}</h2>
        <div>{actions}</div>
      </div>
      {children}
    </section>
  );
}
