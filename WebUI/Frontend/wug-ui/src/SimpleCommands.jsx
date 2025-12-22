import { useState, useEffect } from "react";
import CredentialsSelector from "./components/CredentialsSelector";
import { getAllCredentials } from "./utils/credentials";
import { apiCall } from "./utils/api";

export default function SimpleCommands() {
  const [routers, setRouters] = useState("");
  const [commands, setCommands] = useState("");
  const [selectedCredId, setSelectedCredId] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [enablePassword, setEnablePassword] = useState("");
  const [output, setOutput] = useState("");
  const [showManualFields, setShowManualFields] = useState(true);
  const [configName, setConfigName] = useState("");
  const [logName, setLogName] = useState("");

  useEffect(() => {
    const creds = getAllCredentials();
    if (creds.length > 0 && !selectedCredId) {
      // Auto-select first credential if available
      const firstCred = creds[0];
      setSelectedCredId(firstCred.id);
      setUsername(firstCred.username || "");
      setPassword(firstCred.password || "");
      setEnablePassword(firstCred.enablePassword || "");
      setShowManualFields(false);
    }
  }, [selectedCredId]);

  const handleCredentialSelect = (cred) => {
    if (cred) {
      setSelectedCredId(cred.id);
      setUsername(cred.username);
      setPassword(cred.password);
      setEnablePassword(cred.enablePassword || "");
      setShowManualFields(false);
    } else {
      setSelectedCredId(null);
      setShowManualFields(true);
    }
  };

  const run = async () => {
    // Validation
    if (!routers.trim()) {
      alert("Please enter at least one router");
      return;
    }
    if (!commands.trim()) {
      alert("Please enter config commands");
      return;
    }
    if (!username.trim()) {
      alert("Please enter username or select a saved credential");
      return;
    }
    if (!password.trim()) {
      alert("Please enter password or select a saved credential");
      return;
    }

    const fd = new FormData();
    fd.append("routers", routers.trim());
    fd.append("config", commands.trim());
    fd.append("username", username.trim());
    fd.append("password", password.trim());
    fd.append("enable_password", enablePassword.trim() || "");
    fd.append("config_name", configName.trim());
    fd.append("log_name", logName.trim());

    try {
      const res = await apiCall("routers/run-simple", {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const errorData = await res.json();
        setOutput(
          `Error: ${res.status} ${res.statusText}\n${JSON.stringify(
            errorData,
            null,
            2
          )}`
        );
        return;
      }

      const data = await res.json();
      setOutput(data.stdout || data.stderr || "No output");
    } catch (e) {
      setOutput(`Error: ${e.toString()}`);
    }
  };

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Simple router config</h3>
          <p className="card-subtitle">
            Push a static block of configuration to one or more routers.
          </p>
        </div>
      </div>

      <div className="two-column-layout">
        <div className="form-group">
          <label className="form-label">Routers</label>
          <textarea
            className="textarea"
            placeholder="One router per line (hostname or IP)"
            rows={4}
            value={routers}
            onChange={(e) => setRouters(e.target.value)}
          />
          <span className="helper-text">
            Examples: 10.0.0.1, core-rtr-01, edge-rtr-02
          </span>
        </div>

        <div className="form-group">
          <label className="form-label">Config commands</label>
          <textarea
            className="textarea"
            placeholder={`interface Loopback123\n description Automation test\n ip address 10.10.10.10 255.255.255.255`}
            rows={6}
            value={commands}
            onChange={(e) => setCommands(e.target.value)}
          />
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <CredentialsSelector
          selectedId={selectedCredId}
          onSelect={handleCredentialSelect}
        />
      </div>

      {showManualFields && (
        <div className="form-grid" style={{ marginTop: 12 }}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              className="input"
              placeholder="Device username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="input"
              type="password"
              placeholder="Device password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Enable password (optional)</label>
            <input
              className="input"
              type="password"
              placeholder="If your devices require enable"
              value={enablePassword}
              onChange={(e) => setEnablePassword(e.target.value)}
            />
          </div>
        </div>
      )}

      <div className="form-grid" style={{ marginTop: 18 }}>
        <div className="form-group">
          <label className="form-label">Config name (optional)</label>
          <input
            className="input"
            placeholder="Leave blank for auto-generated name"
            value={configName}
            onChange={(e) => setConfigName(e.target.value)}
          />
          <span className="helper-text">
            Custom name for saved config file. If empty, uses timestamp.
          </span>
        </div>

        <div className="form-group">
          <label className="form-label">Log name (optional)</label>
          <input
            className="input"
            placeholder="Leave blank for auto-generated name"
            value={logName}
            onChange={(e) => setLogName(e.target.value)}
          />
          <span className="helper-text">
            Custom name for saved log file. If empty, uses timestamp.
          </span>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <button className="button button--primary" type="button" onClick={run}>
          <span className="button-icon">▶</span>Run config
        </button>
      </div>

      {output && <pre className="mono-output">{output}</pre>}
    </section>
  );
}
