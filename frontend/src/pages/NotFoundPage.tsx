import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <p className="text-sm font-medium text-surface-500">404</p>
      <h2 className="mt-2 text-lg font-semibold text-surface-50">Page not found</h2>
      <Link to="/" className="focus-ring mt-4 text-sm text-accent hover:text-accent-hover">
        Back to dashboard
      </Link>
    </div>
  );
}
