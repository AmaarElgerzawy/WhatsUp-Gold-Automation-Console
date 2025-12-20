import { useEffect, useState } from "react";

export default function ConfigBackups() {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState("");
  const [files, setFiles] = useState([]);
  const [content, setContent] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/backups/devices")
      .then((res) => res.json())
      .then(setDevices);
  }, []);

  const loadFiles = async (device) => {
    setSelectedDevice(device);
    setContent("");
    const res = await fetch(`http://localhost:8000/backups/${device}`);
    setFiles(await res.json());
  };

  const viewFile = async (file) => {
    const res = await fetch(
      `http://localhost:8000/backups/${selectedDevice}/${file}`
    );
    const text = await res.text();
    setContent(text.replace(/\\n/g, "\n"));
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Config backups</h2>
          <p className="app-main-subtitle">
            Explore device snapshots and inspect configuration history.
          </p>
        </div>
        <span className="pill">Read‑only</span>
      </div>

      <section className="card">
        <div className="two-column-layout" style={{ alignItems: "flex-start" }}>
          {/* Devices */}
          <div>
            <h4 className="card-title" style={{ marginBottom: 8 }}>
              Devices
            </h4>
            <ul className="list">
              {devices.map((d) => (
                <li key={d} style={{ marginBottom: 4 }}>
                  <button
                    type="button"
                    className="list-item-button"
                    onClick={() => loadFiles(d)}
                  >
                    <span>{d}</span>
                    {selectedDevice === d && (
                      <span className="tag">Selected</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Files + content */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "220px minmax(0, 1fr)",
              gap: 12,
            }}
          >
            <div>
              <h4 className="card-title" style={{ marginBottom: 8 }}>
                Configs
              </h4>
              <ul className="list">
                {files.map((f) => (
                  <li key={f} style={{ marginBottom: 4 }}>
                    <button
                      type="button"
                      className="list-item-button"
                      onClick={() => viewFile(f)}
                    >
                      <span>{f}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="card-title" style={{ marginBottom: 8 }}>
                Content
              </h4>
              {content ? (
                <pre className="mono-output">{content}</pre>
              ) : (
                <p className="card-subtitle">
                  Select a device and a backup file to view its content.
                </p>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
