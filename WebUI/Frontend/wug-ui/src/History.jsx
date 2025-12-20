import { useState } from "react";
import SavedConfigs from "./SavedConfigs";
import Logs from "./Logs";

export default function History() {
  const [tab, setTab] = useState("configs");

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">History</h2>
          <p className="app-main-subtitle">
            Browse previously saved configs and inspect execution logs.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            className={
              "button button--sm" +
              (tab === "configs" ? " button--primary" : " button--ghost")
            }
            onClick={() => setTab("configs")}
          >
            Saved configs
          </button>
          <button
            type="button"
            className={
              "button button--sm" +
              (tab === "logs" ? " button--primary" : " button--ghost")
            }
            onClick={() => setTab("logs")}
          >
            Execution logs
          </button>
        </div>
      </div>

      {tab === "configs" && <SavedConfigs />}
      {tab === "logs" && <Logs />}
    </>
  );
}
