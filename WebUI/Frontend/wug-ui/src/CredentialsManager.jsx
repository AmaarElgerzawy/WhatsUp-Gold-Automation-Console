import { useState, useEffect } from "react";
import {
  getAllCredentials,
  saveCredential,
  deleteCredential,
  createCredentialId,
} from "./utils/credentials";

export default function CredentialsManager() {
  const [credentials, setCredentials] = useState([]);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    username: "",
    password: "",
    enablePassword: "",
    description: "",
  });

  useEffect(() => {
    loadCredentials();
  }, []);

  const loadCredentials = () => {
    setCredentials(getAllCredentials());
  };

  const startNew = () => {
    setEditing(null);
    setFormData({
      name: "",
      username: "",
      password: "",
      enablePassword: "",
      description: "",
    });
  };

  const startEdit = (cred) => {
    setEditing(cred);
    setFormData({
      name: cred.name || "",
      username: cred.username || "",
      password: "", // Don't show existing password
      enablePassword: "", // Don't show existing enable password
      description: cred.description || "",
    });
  };

  const handleSave = () => {
    if (!formData.name.trim() || !formData.username.trim()) {
      alert("Name and username are required");
      return;
    }

    // If editing and password fields are empty, keep existing passwords
    const finalPassword = formData.password || editing?.password || "";
    const finalEnablePassword =
      formData.enablePassword || editing?.enablePassword || "";

    if (!finalPassword.trim() && !editing) {
      alert("Password is required for new credentials");
      return;
    }

    const cred = {
      id: editing?.id || createCredentialId(),
      name: formData.name.trim(),
      username: formData.username.trim(),
      password: finalPassword,
      enablePassword: finalEnablePassword,
      description: formData.description.trim(),
      updatedAt: new Date().toISOString(),
    };

    saveCredential(cred);
    loadCredentials();
    startNew();
  };

  const handleDelete = (id) => {
    if (!window.confirm("Delete this credential set?")) return;
    deleteCredential(id);
    loadCredentials();
    if (editing?.id === id) {
      startNew();
    }
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Credentials</h2>
          <p className="app-main-subtitle">
            Store and manage SSH credentials for routers and other devices.
          </p>
        </div>
        <span className="pill">Secure storage</span>
      </div>

      <section className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">
              {editing ? "Edit credential" : "New credential"}
            </h3>
            <p className="card-subtitle">
              {editing
                ? "Update the credential details below"
                : "Create a new credential set to reuse across operations"}
            </p>
          </div>
          <div className="card-actions">
            {editing && (
              <button
                type="button"
                className="button button--ghost button--sm"
                onClick={startNew}
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Name *</label>
            <input
              className="input"
              placeholder="e.g. Production Routers, Lab Devices"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
            />
            <span className="helper-text">
              A friendly name to identify this credential set
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">Username *</label>
            <input
              className="input"
              placeholder="SSH username"
              value={formData.username}
              onChange={(e) =>
                setFormData({ ...formData, username: e.target.value })
              }
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="input"
              type="password"
              placeholder={
                editing
                  ? "Leave blank to keep existing password"
                  : "SSH password"
              }
              value={formData.password}
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
            />
          </div>

          <div className="form-group">
            <label className="form-label">Enable password (optional)</label>
            <input
              className="input"
              type="password"
              placeholder={
                editing
                  ? "Leave blank to keep existing"
                  : "Enable/privileged password"
              }
              value={formData.enablePassword}
              onChange={(e) =>
                setFormData({ ...formData, enablePassword: e.target.value })
              }
            />
          </div>

          <div className="form-group" style={{ gridColumn: "1 / -1" }}>
            <label className="form-label">Description (optional)</label>
            <textarea
              className="textarea"
              rows={2}
              placeholder="Notes about when/where to use this credential set"
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
            />
          </div>
        </div>

        <div style={{ marginTop: 18 }}>
          <button
            type="button"
            className="button button--primary"
            onClick={handleSave}
          >
            <span className="button-icon">💾</span>
            {editing ? "Update credential" : "Save credential"}
          </button>
        </div>
      </section>

      <section className="card" style={{ marginTop: 18 }}>
        <div className="card-header">
          <div>
            <h3 className="card-title">Saved credentials</h3>
            <p className="card-subtitle">
              {credentials.length === 0
                ? "No credentials saved yet"
                : `${credentials.length} credential set${
                    credentials.length !== 1 ? "s" : ""
                  } available`}
            </p>
          </div>
        </div>

        {credentials.length === 0 ? (
          <p
            className="card-subtitle"
            style={{ textAlign: "center", padding: 20 }}
          >
            Create your first credential set above to get started.
          </p>
        ) : (
          <ul className="list">
            {credentials.map((cred) => (
              <li key={cred.id} style={{ marginBottom: 8 }}>
                <div
                  className="card"
                  style={{
                    padding: 12,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 4,
                      }}
                    >
                      <strong>{cred.name}</strong>
                      <span className="tag">{cred.username}</span>
                    </div>
                    {cred.description && (
                      <p
                        className="card-subtitle"
                        style={{ margin: 0, fontSize: 12 }}
                      >
                        {cred.description}
                      </p>
                    )}
                    {cred.updatedAt && (
                      <span className="helper-text" style={{ fontSize: 11 }}>
                        Updated: {new Date(cred.updatedAt).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      type="button"
                      className="button button--ghost button--sm"
                      onClick={() => startEdit(cred)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="button button--danger button--sm"
                      onClick={() => handleDelete(cred.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
