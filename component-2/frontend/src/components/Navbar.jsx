import { NavLink } from "react-router-dom";
import { useState, useEffect } from "react";

const NAV = [
  { to: "/",        label: "MONITOR",  icon: "◉" },
  { to: "/history", label: "HISTORY",  icon: "≡" },
  { to: "/alerts",  label: "ALERTS",   icon: "⚠" },
  { to: "/testing", label: "TESTING",  icon: "▶" },
];

const applyTheme = (theme) => {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("ewaste-theme", theme);
};

const Navbar = () => {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("ewaste-theme") || "dark";
    applyTheme(saved);
    setIsDark(saved === "dark");
  }, []);

  const toggleTheme = () => {
    const next = isDark ? "light" : "dark";
    applyTheme(next);
    setIsDark(!isDark);
  };

  return (
    <nav style={{
      background:   "var(--bg-nav)",
      borderBottom: "1px solid var(--nav-border-bot)",
      boxShadow:    "var(--shadow-sm)",
      position:     "sticky", top: 0, zIndex: 1000,
      transition:   "background 0.25s, border-color 0.25s",
    }}>
      <div style={{ height: "2px", background: "var(--nav-accent-line)" }} />

      <div style={{
        maxWidth: "1200px", margin: "0 auto", padding: "0 20px",
        display: "flex", alignItems: "center",
        justifyContent: "space-between", height: "58px", gap: "8px",
      }}>

        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexShrink: 0 }}>
          <div style={{
            width: "32px", height: "32px", borderRadius: "8px",
            background: "var(--nav-icon-bg)", border: "1px solid var(--nav-icon-border)",
            boxShadow: "var(--nav-icon-glow)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "1rem", flexShrink: 0,
          }}>⚗</div>
          <div>
            <div style={{
              fontFamily: "JetBrains Mono, monospace", fontSize: "0.68rem",
              fontWeight: 700, color: "var(--nav-brand-color)",
              letterSpacing: "0.15em", lineHeight: 1,
            }}>E-WASTE · TOXIC GAS MONITOR</div>
            <div style={{
              fontFamily: "JetBrains Mono, monospace", fontSize: "0.55rem",
              color: "var(--nav-sub-color)", letterSpacing: "0.09em", marginTop: "2px",
            }}>H₂S · CO · NH₃ · C₆H₆ · LPG · WORKER SAFETY</div>
          </div>
        </div>

        {/* Nav links */}
        <div style={{ display: "flex", gap: "2px", alignItems: "center" }}>
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) => isActive ? "nav-active" : ""}
              style={{
                display: "flex", alignItems: "center", gap: "5px",
                padding: "6px 12px", borderRadius: "7px",
                border: "1px solid transparent", textDecoration: "none",
                fontFamily: "JetBrains Mono, monospace", fontSize: "0.68rem",
                fontWeight: 600, letterSpacing: "0.10em",
                color: "var(--nav-link-color)", transition: "all 0.18s",
              }}
            >
              <span style={{ fontSize: "0.82rem", lineHeight: 1 }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </div>

        {/* Right controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "7px", flexShrink: 0 }}>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            title={isDark ? "Switch to Light mode" : "Switch to Dark mode"}
            style={{
              display: "flex", alignItems: "center", gap: "5px",
              padding: "5px 11px", borderRadius: "20px",
              border: "1px solid var(--toggle-border)",
              background: "var(--toggle-bg)", color: "var(--toggle-color)",
              fontFamily: "JetBrains Mono, monospace", fontSize: "0.62rem",
              fontWeight: 600, letterSpacing: "0.07em", cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            <span style={{ fontSize: "0.88rem", lineHeight: 1 }}>{isDark ? "☀" : "🌙"}</span>
            {isDark ? "LIGHT" : "DARK"}
          </button>

          {/* System badge */}
          <div style={{
            display: "flex", alignItems: "center", gap: "5px",
            padding: "5px 11px", borderRadius: "20px",
            background: "var(--nav-badge-bg)", border: "1px solid var(--nav-badge-border)",
          }}>
            <span className="dot-active" />
            <span style={{
              fontFamily: "JetBrains Mono, monospace", fontSize: "0.58rem",
              fontWeight: 600, color: "var(--nav-badge-color)", letterSpacing: "0.09em",
            }}>ACTIVE</span>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
