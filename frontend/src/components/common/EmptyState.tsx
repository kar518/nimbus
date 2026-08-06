import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-surface-800 bg-surface-900/40 px-6 py-16 text-center">
      <Icon className="mb-3 h-6 w-6 text-surface-500" aria-hidden="true" />
      <p className="text-sm font-medium text-surface-200">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-surface-500">{description}</p>
    </div>
  );
}
