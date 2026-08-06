import type { PropsWithChildren, ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({
  title,
  description,
  actions,
  children,
}: PropsWithChildren<PageHeaderProps>) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h2 className="text-lg font-semibold text-surface-50">{title}</h2>
        {description && <p className="mt-1 text-sm text-surface-400">{description}</p>}
        {children}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
