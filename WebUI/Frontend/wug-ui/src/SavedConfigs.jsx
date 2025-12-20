import { useEffect, useState } from "react";

const SECTIONS = [
  "bulk_add",
  "bulk_update",
  "bulk_delete",
  "router_simple",
  "router_interactive",
];

export default function SavedConfigs() {
  const [section, setSection] = useState(SECTIONS[0]);
  const [files, setFiles] = useState([]);
  const [content, setContent] = useState("");
  const [editingName, setEditingName] = useState(null);
  const [newName, setNewName] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);

  const loadFiles = async () => {
    const res = await fetch(`http://localhost:8000/configs/${section}`);
    setFiles(await res.json());
  };

  const viewFile = async (name) => {
    setSelectedFile(name);
    const res = await fetch(`http://localhost:8000/configs/${section}/${name}`);
    const text = await res.text();
    setContent(text.replace(/\\n/g, "\n"));
  };

  const deleteFile = async (name) => {
    if (!window.confirm("Delete this config?")) return;
    await fetch(`http://localhost:8000/configs/${section}/${name}`, {
      method: "DELETE",
    });
    if (selectedFile === name) {
      setContent("");
      setSelectedFile(null);
    }
    loadFiles();
  };

  const startRename = (name) => {
    setEditingName(name);
    // Remove extension for editing
    const nameWithoutExt = name.replace(/\.[^/.]+$/, "");
    setNewName(nameWithoutExt);
  };

  const cancelRename = () => {
    setEditingName(null);
    setNewName("");
  };

  const saveRename = async (oldName) => {
    if (!newName.trim()) {
      alert("Name cannot be empty");
      return;
    }

    try {
      const res = await fetch(
        `http://localhost:8000/configs/${section}/${oldName}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ new_name: newName.trim() }),
        }
      );

      if (!res.ok) {
        const error = await res.json();
        alert(`Error: ${error.detail || "Failed to rename"}`);
        return;
      }

      const data = await res.json();
      setEditingName(null);
      setNewName("");

      // If this was the selected file, update selection
      if (selectedFile === oldName) {
        setSelectedFile(data.new_name);
        viewFile(data.new_name);
      }

      loadFiles();
    } catch (e) {
      alert(`Error: ${e.toString()}`);
    }
  };

  const downloadFile = async (name) => {
    try {
      const res = await fetch(
        `http://localhost:8000/configs/${section}/${name}?download=true`
      );
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      alert(`Error downloading file: ${e.toString()}`);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [section]);

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Saved configurations</h3>
          <p className="card-subtitle">
            Browse and manage snapshots produced by bulk and router operations.
          </p>
        </div>
      </div>

      <div className="two-column-layout">
        <div>
          <div className="form-group">
            <label className="form-label">Config type</label>
            <select
              className="select"
              value={section}
              onChange={(e) => setSection(e.target.value)}
            >
              {SECTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <ul className="list" style={{ marginTop: 10 }}>
            {files.map((f) => (
              <li key={f} style={{ marginBottom: 4 }}>
                {editingName === f ? (
                  <div
                    className="card"
                    style={{
                      padding: 8,
                      display: "flex",
                      gap: 6,
                      alignItems: "center",
                    }}
                  >
                    <input
                      className="input"
                      style={{ flex: 1, fontSize: 12 }}
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveRename(f);
                        if (e.key === "Escape") cancelRename();
                      }}
                      autoFocus
                    />
                    <button
                      type="button"
                      className="button button--primary button--sm"
                      onClick={() => saveRename(f)}
                    >
                      ✓
                    </button>
                    <button
                      type="button"
                      className="button button--ghost button--sm"
                      onClick={cancelRename}
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="list-item-button"
                    onClick={() => viewFile(f)}
                  >
                    <span style={{ flex: 1, textAlign: "left" }}>{f}</span>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        type="button"
                        className="button button--ghost button--sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadFile(f);
                        }}
                        title="Download"
                      >
                        ⬇
                      </button>
                      <button
                        type="button"
                        className="button button--ghost button--sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          startRename(f);
                        }}
                        title="Rename"
                      >
                        ✏
                      </button>
                      <button
                        type="button"
                        className="button button--danger button--sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteFile(f);
                        }}
                        title="Delete"
                      >
                        ✕
                      </button>
                    </div>
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <h4 className="card-title" style={{ margin: 0 }}>
              Content
            </h4>
            {selectedFile && (
              <button
                type="button"
                className="button button--ghost button--sm"
                onClick={() => downloadFile(selectedFile)}
              >
                <span className="button-icon">⬇</span>Download
              </button>
            )}
          </div>
          {content ? (
            <pre className="mono-output">{content}</pre>
          ) : (
            <p className="card-subtitle">
              Select a config file to inspect its content.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
