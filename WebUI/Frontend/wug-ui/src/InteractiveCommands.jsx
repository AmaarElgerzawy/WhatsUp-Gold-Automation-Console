import { useState, useEffect } from "react";
import CredentialsSelector from "./components/CredentialsSelector";
import { getAllCredentials } from "./utils/credentials";

export default function InteractiveCommands() {
  const [routers, setRouters] = useState("");
  const [tasks, setTasks] = useState([]);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedCredId, setSelectedCredId] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [enablePassword, setEnablePassword] = useState("");
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

  const addTask = (type) => {
    if (type === "config") {
      setTasks([...tasks, { type, commands: [""] }]);
    } else if (type === "exec") {
      setTasks([...tasks, { type, command: "" }]);
    } else if (type === "interactive_exec") {
      setTasks([...tasks, { type, command: "", steps: [] }]);
    } else if (type === "write_memory") {
      setTasks([...tasks, { type }]);
    }
  };

  const updateTask = (i, updated) => {
    const copy = [...tasks];
    copy[i] = updated;
    setTasks(copy);
  };

  const removeTask = (i) => {
    setTasks(tasks.filter((_, idx) => idx !== i));
  };

  const run = async () => {
    // Validation
    if (!routers.trim()) {
      alert("Please enter at least one router");
      return;
    }
    if (tasks.length === 0) {
      alert("Please add at least one task");
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

    setLoading(true);
    setOutput("");
    setError("");

    const formData = new FormData();
    formData.append("routers", routers.trim());
    formData.append("tasks_json", JSON.stringify(tasks, null, 2));
    formData.append("username", username.trim());
    formData.append("password", password.trim());
    formData.append("enable_password", enablePassword.trim() || "");
    formData.append("config_name", configName.trim());
    formData.append("log_name", logName.trim());

    try {
      const res = await fetch("http://localhost:8000/routers/run-interactive", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        setError(JSON.stringify(data, null, 2));
        return;
      }

      setOutput(
        `EXIT CODE: ${data.returncode}\n\n` +
          `STDOUT:\n${data.stdout}\n\n` +
          `STDERR:\n${data.stderr}`
      );
    } catch (e) {
      setError(e.toString());
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Interactive commands builder</h3>
          <p className="card-subtitle">
            Chain config, exec, and interactive steps into a single run.
          </p>
        </div>
      </div>

      <div className="two-column-layout">
        <div className="form-group">
          <label className="form-label">Routers</label>
          <textarea
            className="textarea"
            rows={4}
            placeholder="One router per line"
            value={routers}
            onChange={(e) => setRouters(e.target.value)}
          />
        </div>

        <div>
          <CredentialsSelector
            selectedId={selectedCredId}
            onSelect={handleCredentialSelect}
          />
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
                  placeholder="Enable password"
                  value={enablePassword}
                  onChange={(e) => setEnablePassword(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: 18, marginBottom: 12 }}>
        <span className="form-label">Tasks</span>
        <div
          style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}
        >
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={() => addTask("config")}
          >
            + Config block
          </button>
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={() => addTask("exec")}
          >
            + Exec
          </button>
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={() => addTask("interactive_exec")}
          >
            + Interactive exec
          </button>
          <button
            type="button"
            className="button button--ghost button--sm"
            onClick={() => addTask("write_memory")}
          >
            + Write memory
          </button>
        </div>
      </div>

      {tasks.map((task, i) => (
        <div key={i} className="card" style={{ marginTop: 10, padding: 12 }}>
          <div className="card-header" style={{ marginBottom: 10 }}>
            <div className="tag">
              {task.type === "config" && "Config"}
              {task.type === "exec" && "Exec"}
              {task.type === "interactive_exec" && "Interactive exec"}
              {task.type === "write_memory" && "Write memory"}
            </div>
            <button
              type="button"
              className="button button--danger button--sm"
              onClick={() => removeTask(i)}
            >
              ✕ Remove
            </button>
          </div>

          {/* CONFIG */}
          {task.type === "config" && (
            <textarea
              className="textarea"
              rows={4}
              value={task.commands.join("\n")}
              onChange={(e) =>
                updateTask(i, {
                  ...task,
                  commands: e.target.value.split("\n"),
                })
              }
              placeholder="interface Loopback123&#10; description Change via automation"
            />
          )}

          {/* EXEC */}
          {task.type === "exec" && (
            <input
              className="input"
              value={task.command}
              onChange={(e) =>
                updateTask(i, { ...task, command: e.target.value })
              }
              placeholder="show ip interface brief"
            />
          )}

          {/* INTERACTIVE */}
          {task.type === "interactive_exec" && (
            <>
              <input
                className="input"
                style={{ marginBottom: 8 }}
                value={task.command}
                onChange={(e) =>
                  updateTask(i, { ...task, command: e.target.value })
                }
                placeholder="delete flash:test.txt"
              />

              {task.steps.map((s, idx) => (
                <div
                  key={idx}
                  style={{ display: "flex", gap: 6, marginBottom: 6 }}
                >
                  <input
                    className="input"
                    placeholder="Prompt"
                    value={s.prompt}
                    onChange={(e) => {
                      const steps = [...task.steps];
                      steps[idx].prompt = e.target.value;
                      updateTask(i, { ...task, steps });
                    }}
                  />
                  <input
                    className="input"
                    placeholder="Answer"
                    value={s.answer}
                    onChange={(e) => {
                      const steps = [...task.steps];
                      steps[idx].answer = e.target.value;
                      updateTask(i, { ...task, steps });
                    }}
                  />
                </div>
              ))}

              <button
                type="button"
                className="button button--ghost button--sm"
                onClick={() =>
                  updateTask(i, {
                    ...task,
                    steps: [...task.steps, { prompt: "", answer: "" }],
                  })
                }
              >
                + Step
              </button>
            </>
          )}

          {/* WRITE MEMORY */}
          {task.type === "write_memory" && (
            <p className="card-subtitle">
              Save configuration to NVRAM (<code>write memory</code>).
            </p>
          )}
        </div>
      ))}

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
        <button
          type="button"
          className="button button--primary"
          onClick={run}
          disabled={loading}
        >
          <span className="button-icon">▶</span>
          {loading ? "Running…" : "Run interactive commands"}
        </button>
      </div>

      {error && <pre className="mono-output mono-output--error">{error}</pre>}
      {output && <pre className="mono-output">{output}</pre>}
    </section>
  );
}
