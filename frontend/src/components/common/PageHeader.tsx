import type { ReactNode } from "react";
export function PageHeader({
  title,
  description,
  action,
  eyebrow = "WORKSPACE",
}: {
  title: string;
  description: string;
  action?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {action && <div className="heading-action">{action}</div>}
    </div>
  );
}
