import { useState, useEffect } from "react";
import BulkChanges from "./BulkChanges";
import RouterCommands from "./RouterCommands";
import History from "./History";
import ConfigBackups from "./ConfigBackups";
import ReportSchedule from "./ReportSchedule";
import BackupRouters from "./BackupRouters";
import CredentialsManager from "./CredentialsManager";
import Admin from "./Admin";
import Login from "./Login";
import ProtectedRoute from "./components/ProtectedRoute";
import ManualReports from "./ManualReports";
import { checkAuth, logout as authLogout, getUser } from "./utils/auth";

export default function App() {
  const [page, setPage] = useState("bulk");
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check authentication on mount
    const verifyAuth = async () => {
      const authenticatedUser = await checkAuth();
      setUser(authenticatedUser);
      setLoading(false);
    };
    verifyAuth();
  }, []);

  // Ensure current page is accessible, redirect to first available page if not
  useEffect(() => {
    if (!user || !user.privileges || !Array.isArray(user.privileges)) return;

    const pagePrivilegeMap = {
      bulk: "bulk_operations",
      routers: "router_commands",
      history: "view_history",
      backups: "view_backups",
      reports: "manage_reports",
      generatereports: "manage_reports",
      credentials: "manage_credentials",
      admin: "admin_access",
    };

    const requiredPrivilege = pagePrivilegeMap[page];
    if (requiredPrivilege && !user.privileges.includes(requiredPrivilege)) {
      // Find first available page
      const availablePage = Object.keys(pagePrivilegeMap).find((p) =>
        user.privileges.includes(pagePrivilegeMap[p])
      );
      if (availablePage) {
        setPage(availablePage);
      }
    }
  }, [user, page]);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    authLogout();
    setUser(null);
  };

  // Show loading state
  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "radial-gradient(circle at top, #1f2937 0, #020617 55%)",
        }}
      >
        <p className="card-subtitle">Loading...</p>
      </div>
    );
  }

  // Show login if not authenticated
  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app-root">
      {/* Global header */}
      <header className="app-header">
        <div className="app-header-title">
          <span>WhatsUp Automation</span>
          <h1>Network Automation Console</h1>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 13, color: "#9ca3af" }}>
              {user.username}
            </div>
            <div style={{ fontSize: 11, color: "#6b7280" }}>{user.role}</div>
          </div>
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </header>

      {/* Shell with nav + main content */}
      <div className="app-shell">
        {/* Side navigation */}
        <nav className="app-nav">
          {user.privileges &&
            Array.isArray(user.privileges) &&
            user.privileges.includes("bulk_operations") && (
              <div className="app-nav-group">
                <div className="app-nav-section-label">Bulk operations</div>
                <button
                  className={
                    "nav-button" +
                    (page === "bulk" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("bulk")}
                >
                  <span className="nav-button-icon">⚙️</span>
                  <div className="nav-button-label">
                    Bulk device changes
                    <div className="nav-button-sub">
                      Import from Excel & push at scale
                    </div>
                  </div>
                </button>
              </div>
            )}

          {user.privileges &&
            Array.isArray(user.privileges) &&
            user.privileges.includes("router_commands") && (
              <div className="app-nav-group">
                <div className="app-nav-section-label">Routers</div>
                <button
                  className={
                    "nav-button" +
                    (page === "routers" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("routers")}
                >
                  <span className="nav-button-icon">📡</span>
                  <div className="nav-button-label">
                    Router commands
                    <div className="nav-button-sub">
                      Simple & interactive command runs
                    </div>
                  </div>
                </button>
              </div>
            )}

          {user.privileges &&
            Array.isArray(user.privileges) &&
            user.privileges.includes("view_history") && (
              <div className="app-nav-group">
                <div className="app-nav-section-label">History</div>
                <button
                  className={
                    "nav-button" +
                    (page === "history" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("history")}
                >
                  <span className="nav-button-icon">🕒</span>
                  <div className="nav-button-label">
                    Runs & configs
                    <div className="nav-button-sub">
                      Saved configs and execution logs
                    </div>
                  </div>
                </button>
              </div>
            )}

          <div className="app-nav-group">
            <div className="app-nav-section-label">Backups & reports</div>
            {user.privileges &&
              Array.isArray(user.privileges) &&
              user.privileges.includes("view_backups") && (
                <button
                  className={
                    "nav-button" +
                    (page === "backups" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("backups")}
                >
                  <span className="nav-button-icon">💾</span>
                  <div className="nav-button-label">
                    Config backups
                    <div className="nav-button-sub">
                      Browse device snapshots
                    </div>
                  </div>
                </button>
              )}

            {user.privileges &&
              Array.isArray(user.privileges) &&
              user.privileges.includes("manage_reports") && (
                <button
                  className={
                    "nav-button" +
                    (page === "reports" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("reports")}
                >
                  <span className="nav-button-icon">📊</span>
                  <div className="nav-button-label">
                    Report schedule
                    <div className="nav-button-sub">
                      Control recurring exports
                    </div>
                  </div>
                </button>
              )}

            {user.privileges &&
              Array.isArray(user.privileges) &&
              user.privileges.includes("manage_reports") && (
                <button
                  className={
                    "nav-button" +
                    (page === "generatereports" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("generatereports")}
                >
                  <span className="nav-button-icon">📊</span>
                  <div className="nav-button-label">
                    Generate Manual Report
                    <div className="nav-button-sub">
                      Control recurring exports
                    </div>
                  </div>
                </button>
              )}
          </div>

          {user.privileges &&
            Array.isArray(user.privileges) &&
            user.privileges.includes("manage_credentials") && (
              <div className="app-nav-group">
                <div className="app-nav-section-label">Settings</div>
                <button
                  className={
                    "nav-button" +
                    (page === "credentials" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("credentials")}
                >
                  <span className="nav-button-icon">🔐</span>
                  <div className="nav-button-label">
                    Credentials
                    <div className="nav-button-sub">
                      Manage SSH & device credentials
                    </div>
                  </div>
                </button>
              </div>
            )}

          {user.privileges &&
            Array.isArray(user.privileges) &&
            user.privileges.includes("admin_access") && (
              <div className="app-nav-group">
                <div className="app-nav-section-label">Administration</div>
                <button
                  className={
                    "nav-button" +
                    (page === "admin" ? " nav-button--active" : "")
                  }
                  onClick={() => setPage("admin")}
                >
                  <span className="nav-button-icon">👤</span>
                  <div className="nav-button-label">
                    Admin
                    <div className="nav-button-sub">
                      User management & activity logs
                    </div>
                  </div>
                </button>
              </div>
            )}
        </nav>

        {/* Main area */}
        <main className="app-main">
          {page === "bulk" && (
            <ProtectedRoute page="bulk" user={user}>
              <BulkChanges />
            </ProtectedRoute>
          )}
          {page === "routers" && (
            <ProtectedRoute page="routers" user={user}>
              <RouterCommands />
            </ProtectedRoute>
          )}
          {page === "history" && (
            <ProtectedRoute page="history" user={user}>
              <History />
            </ProtectedRoute>
          )}
          {page === "backups" && (
            <ProtectedRoute page="backups" user={user}>
              <BackupRouters />
              <ConfigBackups />
            </ProtectedRoute>
          )}
          {page === "reports" && (
            <ProtectedRoute page="reports" user={user}>
              <ReportSchedule />
            </ProtectedRoute>
          )}
          {page === "generatereports" && (
            <ProtectedRoute page="generatereports" user={user}>
              <ManualReports />
            </ProtectedRoute>
          )}
          {page === "credentials" && (
            <ProtectedRoute page="credentials" user={user}>
              <CredentialsManager />
            </ProtectedRoute>
          )}
          {page === "admin" && (
            <ProtectedRoute page="admin" user={user}>
              <Admin />
            </ProtectedRoute>
          )}
        </main>
      </div>
    </div>
  );
}
