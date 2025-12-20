import { useState } from "react";

function BulkChnages() {
  const [operation, setOperation] = useState("add");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");
  const [configName, setConfigName] = useState("");
  const [logName, setLogName] = useState("");

  const run = async () => {
    if (!file) {
      alert("Select an Excel file");
      return;
    }

    setLoading(true);
    setOutput("");
    setError("");

    const formData = new FormData();
    formData.append("operation", operation);
    formData.append("file", file);
    formData.append("config_name", configName.trim());
    formData.append("log_name", logName.trim());

    try {
      const res = await fetch("http://localhost:8000/run", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        setError(JSON.stringify(data, null, 2));
        setLoading(false);
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
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Bulk device operations</h2>
          <p className="app-main-subtitle">
            Import an Excel sheet and safely apply large‑scale changes.
          </p>
        </div>
        <span className="pill">Excel driven</span>
      </div>

      <section className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Upload & run</h3>
            <p className="card-subtitle">
              Select the action and the Excel file that contains your devices.
            </p>
          </div>
          <div className="card-actions">
            <button className="button button--ghost button--sm" type="button">
              <span className="button-icon">📄</span>Template
            </button>
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Operation</label>
            <select
              className="select"
              value={operation}
              onChange={(e) => setOperation(e.target.value)}
            >
              <option value="add">Add devices</option>
              <option value="delete">Delete devices</option>
              <option value="update">Update devices</option>
            </select>
            <span className="helper-text">
              Choose what you want to do with the devices listed in the Excel
              file.
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">Excel file (.xlsx)</label>
            <input
              className="input"
              type="file"
              accept=".xlsx"
              onChange={(e) => setFile(e.target.files[0])}
            />
            <span className="helper-text">
              The first row should contain column headers.
            </span>
          </div>
        </div>

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

        <div style={{ marginTop: 20, display: "flex", gap: 10 }}>
          <button
            className="button button--primary"
            onClick={run}
            disabled={loading}
            type="button"
          >
            <span className="button-icon">▶</span>
            {loading ? "Running…" : "Run bulk operation"}
          </button>
        </div>

        {error && <pre className="mono-output mono-output--error">{error}</pre>}

        {output && !error && <pre className="mono-output">{output}</pre>}
      </section>
    </>
  );
}

export default BulkChnages;
