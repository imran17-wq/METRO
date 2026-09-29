/**
 * NavBar.tsx — Operations Control Center Top Navigation Bar.
 * Clean, consolidated 4-primary + 1-secondary navigation structure.
 */
import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useStore } from "../../store/useStore";

const links = [
  { to: "/", label: "CONTROL CENTER" },
  { to: "/planner", label: "ROUTES" },
  { to: "/incidents", label: "INCIDENTS" },
  { to: "/analysis", label: "ANALYSIS" },
  { to: "/about", label: "DATA / ABOUT" },
];

const NavBar: React.FC = () => {
  const { pathname } = useLocation();
  const { activeScenario } = useStore();

  return (
    <nav
      className="flex items-center justify-between px-5 py-3 border-b border-dark-border bg-dark-surface/80 backdrop-blur-sm sticky top-0 z-40"
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo / wordmark */}
      <Link to="/" className="flex items-center gap-2.5 group" aria-label="Namma Pulse OCC home">
        <div className="flex gap-1">
          <div className="w-2.5 h-2.5 rounded-full bg-[#7B2D8B]" title="Purple Line" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#2A7D4F]" title="Green Line" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#D4A017]" title="Yellow Line" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#E05297]" title="Pink Line (Simulated Service)" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#00A3E0]" title="Blue Line (Simulated Service)" />
        </div>
        <div>
          <span className="font-heading text-cream text-sm tracking-[0.08em] uppercase">
            Namma Pulse
          </span>
          <span className="block text-cream/40 text-[9px] font-data tracking-widest uppercase leading-tight">
            Metro Operations Control Center
          </span>
        </div>
      </Link>

      {/* Links */}
      <div className="flex items-center gap-1.5 overflow-x-auto">
        {links.map(({ to, label }) => {
          const isActive = pathname === to || (to === "/analysis" && pathname.startsWith("/analysis"));
          return (
            <Link
              key={to}
              to={to}
              className={`nav-link text-xs whitespace-nowrap px-3 py-1.5 rounded transition-all font-data uppercase tracking-wider ${
                isActive ? "nav-link-active font-semibold bg-rust/20 text-rust border border-rust/30" : "text-cream/60 hover:text-cream"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </div>

      {/* Status pill */}
      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-dark-card border border-dark-border flex-shrink-0">
        <div className={`w-2 h-2 rounded-full ${activeScenario ? "bg-rust animate-pulse" : "bg-emerald-400 animate-pulse-soft"}`} />
        <span className="text-cream text-[10px] font-data uppercase tracking-wide">
          {activeScenario ? `🔴 ${activeScenario.name.toUpperCase()}` : "🟢 NORMAL"}
        </span>
      </div>
    </nav>
  );
};

export default NavBar;
