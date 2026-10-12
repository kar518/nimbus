import { NavLink, Link } from "react-router-dom";
import { ChevronDown, LogOut, Plus } from "lucide-react";
import { Logo } from "@/components/common/UI";
import { useSession } from "@/hooks/useSession";
import { NAV_ITEMS } from "@/utils/navigation";
export function Sidebar() {
  const { user, logout } = useSession();
  return (
    <aside className="sidebar">
      <Link to="/" className="brand-link" aria-label="Nimbus overview">
        <Logo />
      </Link>
      <div className="workspace-switch">
        <span className="workspace-avatar">N</span>
        <span>
          <strong>Compute workspace</strong>
          <small>Your connected cluster</small>
        </span>
        <ChevronDown size={14} />
      </div>
      <p className="sidebar-label">WORKSPACE</p>
      <nav aria-label="Primary">
        {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-tip">
          <span className="tip-icon">
            <Plus size={18} />
          </span>
          <strong>Make room for your ideas.</strong>
          <p>Bring a workload. Nimbus handles the queue.</p>
          <Link className="button small secondary full" to="/jobs/new">
            Submit a workload
            <Plus size={14} />
          </Link>
        </div>
        <div className="user-row">
          <span className="user-avatar">{user?.username.slice(0, 2).toUpperCase()}</span>
          <span>
            <strong>{user?.username}</strong>
            <small>{user?.is_admin ? "Administrator" : "Member"}</small>
          </span>
          <button
            className="icon-button"
            aria-label="Sign out"
            onClick={() => {
              void logout();
            }}
          >
            <LogOut size={16} />
          </button>
        </div>
        <div className="sidebar-version">
          Nimbus v0.2 <span>Docker execution</span>
        </div>
      </div>
    </aside>
  );
}
