import type { LucideIcon } from "lucide-react";
import { Cpu, LayoutDashboard, Layers, ScrollText, History, Settings } from "lucide-react";
export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}
export const NAV_ITEMS: NavItem[] = [
  { label: "Overview", to: "/", icon: LayoutDashboard },
  { label: "Workloads", to: "/queue", icon: Layers },
  { label: "Workers", to: "/workers", icon: Cpu },
  { label: "History", to: "/history", icon: History },
  { label: "Logs", to: "/logs", icon: ScrollText },
  { label: "Settings", to: "/settings", icon: Settings },
];
