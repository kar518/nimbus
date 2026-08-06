import type { LucideIcon } from "lucide-react";
import { Cpu, LayoutDashboard, ListOrdered, ScrollText, History } from "lucide-react";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard },
  { label: "Queue", to: "/queue", icon: ListOrdered },
  { label: "GPU Workers", to: "/workers", icon: Cpu },
  { label: "Execution History", to: "/history", icon: History },
  { label: "Logs", to: "/logs", icon: ScrollText },
];
