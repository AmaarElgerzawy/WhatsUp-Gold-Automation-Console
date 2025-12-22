import { useState } from "react";
import SimpleCommands from "./SimpleCommands";
import InteractiveCommands from "./InteractiveCommands";

export default function RouterCommands() {
  const [tab, setTab] = useState("simple");

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Router commands</h2>
          <p className="app-main-subtitle">
            Run one‑off or interactive command sequences against your routers.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", gap: 8 }}>
        <button
            type="button"
            className={
              "button button--sm" +
              (tab === "simple" ? " button--primary" : " button--ghost")
            }
          onClick={() => setTab("simple")}
        >
            Simple config
        </button>

        <button
            type="button"
            className={
              "button button--sm" +
              (tab === "interactive" ? " button--primary" : " button--ghost")
            }
          onClick={() => setTab("interactive")}
        >
            Interactive builder
        </button>
        </div>
      </div>

      {tab === "simple" && <SimpleCommands />}
      {tab === "interactive" && <InteractiveCommands />}
    </>
  );
}
