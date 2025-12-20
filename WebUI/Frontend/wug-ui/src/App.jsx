import { useState } from "react";
import BulkChanges from "./BulkChanges";
import RouterCommands from "./RouterCommands";
import History from "./History";
import ConfigBackups from "./ConfigBackups";
import ReportSchedule from "./ReportSchedule";
import BackupRouters from "./BackupRouters";
import CredentialsManager from "./CredentialsManager";

export default function App() {
  const [page, setPage] = useState("bulk");

  return (
    <div className="app-root">
      {/* Global header */}
      <header className="app-header">
        <div className="app-header-title">
          <span>WhatsUp Automation</span>
          <h1>Network Automation Console</h1>
        </div>
        <div className="app-header-badge">Operator Workspace</div>
      </header>

      {/* Shell with nav + main content */}
      <div className="app-shell">
        {/* Side navigation */}
        <nav className="app-nav">
          <div className="app-nav-group">
            <div className="app-nav-section-label">Bulk operations</div>
            <button
              className={
                "nav-button" + (page === "bulk" ? " nav-button--active" : "")
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

          <div className="app-nav-group">
            <div className="app-nav-section-label">Routers</div>
            <button
              className={
                "nav-button" + (page === "routers" ? " nav-button--active" : "")
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

          <div className="app-nav-group">
            <div className="app-nav-section-label">History</div>
            <button
              className={
                "nav-button" + (page === "history" ? " nav-button--active" : "")
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

          <div className="app-nav-group">
            <div className="app-nav-section-label">Backups & reports</div>
            <button
              className={
                "nav-button" + (page === "backups" ? " nav-button--active" : "")
              }
              onClick={() => setPage("backups")}
            >
              <span className="nav-button-icon">💾</span>
              <div className="nav-button-label">
                Config backups
                <div className="nav-button-sub">Browse device snapshots</div>
              </div>
            </button>

            <button
              className={
                "nav-button" + (page === "reports" ? " nav-button--active" : "")
              }
              onClick={() => setPage("reports")}
            >
              <span className="nav-button-icon">📊</span>
              <div className="nav-button-label">
                Report schedule
                <div className="nav-button-sub">Control recurring exports</div>
              </div>
            </button>
          </div>

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
        </nav>

        {/* Main area */}
        <main className="app-main">
          {page === "bulk" && <BulkChanges />}
          {page === "routers" && <RouterCommands />}
          {page === "history" && <History />}
          {page === "backups" && <BackupRouters />}
          {page === "backups" && <ConfigBackups />}
          {page === "reports" && <ReportSchedule />}
          {page === "credentials" && <CredentialsManager />}
        </main>
      </div>
    </div>
  );
}
