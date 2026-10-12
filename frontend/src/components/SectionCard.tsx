import type { PropsWithChildren, ReactNode } from "react";

type Props = PropsWithChildren<{
  title: string;
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
}>;

export function SectionCard({ title, actions, className, bodyClassName, children }: Props) {
  return (
    <section className={`card ${className ?? ""}`.trim()}>
      <div className="card-header">
        <h2>{title}</h2>
        <div>{actions}</div>
      </div>
      <div className={`card-body ${bodyClassName ?? ""}`.trim()}>
        {children}
      </div>
    </section>
  );
}
