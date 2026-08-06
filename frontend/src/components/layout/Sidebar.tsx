import { clsx } from "clsx";
import { NavLink } from "react-router-dom";

import { NAV_ITEMS } from "@/utils/navigation";

export function Sidebar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-surface-800 bg-surface-900">
      <div className="flex h-16 items-center gap-2 border-b border-surface-800 px-5">
        <div className="h-2.5 w-2.5 rounded-full bg-accent" aria-hidden="true" />
        <span className="text-sm font-semibold tracking-wide text-surface-50">NIMBUS</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Primary">
        {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "focus-ring flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-surface-800 text-surface-50"
                  : "text-surface-400 hover:bg-surface-800/60 hover:text-surface-100"
              )
            }
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-surface-800 px-5 py-4 text-xs text-surface-500">
        v0.1.0 &middot; scaffold
      </div>
    </aside>
  );
}
