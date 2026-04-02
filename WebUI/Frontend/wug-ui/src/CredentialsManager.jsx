import { useState, useEffect } from "react";
import { getUser } from "./utils/auth";
import {
  fetchAdminCredentials,
  fetchEligibleCredentials,
  createAdminCredential,
  updateAdminCredential,
  deleteAdminCredential,
} from "./utils/credentials";

export default function CredentialsManager() {
  const user = getUser();
  const isAdmin = user?.privileges?.includes("admin_access");

  const [credentials, setCredentials] = useState([]);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    username: "",
    password: "",
    enablePassword: "",
    description: "",
  });

  const loadCredentials = async () => {
    if (isAdmin) {
      const list = await fetchAdminCredentials();
      setCredentials(Array.isArray(list) ? list : []);
    } else {
      const list = await fetchEligibleCredentials();
      setCredentials(Array.isArray(list) ? list : []);
    }
  };

  useEffect(() => {
    loadCredentials();
  }, [isAdmin]);

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
      password: "",
      enablePassword: "",
      description: cred.description || "",
    });
  };

  const notifyVaultChanged = () => {
    window.dispatchEvent(new Event("credentialsUpdated"));
  };

  const handleSave = async () => {
    if (!isAdmin) return;
    if (!formData.name.trim() || !formData.username.trim()) {
      alert("Name and username are required");
      return;
    }

    if (!editing && !formData.password.trim()) {
      alert("Password is required for new credentials");
      return;
    }

    try {
      if (editing) {
        const res = await updateAdminCredential(editing.id, {
          name: formData.name,
          username: formData.username,
          password: formData.password.trim() ? formData.password : undefined,
          enablePassword: formData.enablePassword.trim()
            ? formData.enablePassword
            : undefined,
          description: formData.description,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          alert(err.detail || "Failed to update credential");
          return;
        }
      } else {
        const res = await createAdminCredential({
          name: formData.name,
          username: formData.username,
          password: formData.password,
          enablePassword: formData.enablePassword || "",
          description: formData.description,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          alert(err.detail || "Failed to create credential");
          return;
        }
      }
      notifyVaultChanged();
      await loadCredentials();
      startNew();
    } catch (e) {
      alert(`Error: ${e.toString()}`);
    }
  };

  const handleDelete = async (id) => {
    if (!isAdmin) return;
    if (!window.confirm("Delete this credential set?")) return;
    try {
      const res = await deleteAdminCredential(id);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Failed to delete");
        return;
      }
      notifyVaultChanged();
      await loadCredentials();
      if (editing?.id === id) {
        startNew();
      }
    } catch (e) {
      alert(`Error: ${e.toString()}`);
    }
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Credentials</h2>
          <p className="app-main-subtitle">
            {isAdmin
              ? "Create and manage SSH credential sets on the server. Assign which sets each user may use in Admin → Users."
              : "Credential sets your administrator assigned to you (passwords are not shown)."}
          </p>
        </div>
        <span className="pill">{isAdmin ? "Admin" : "Assigned sets"}</span>
      </div>

      {isAdmin && (
        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                {editing ? "Edit credential" : "New credential"}
              </h3>
              <p className="card-subtitle">
                {editing
                  ? "Update the credential details below"
                  : "Create a credential set stored on the server"}
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
      )}

      <section className="card" style={{ marginTop: isAdmin ? 18 : 0 }}>
        <div className="card-header">
          <div>
            <h3 className="card-title">
              {isAdmin ? "Saved credentials" : "Your assigned credential sets"}
            </h3>
            <p className="card-subtitle">
              {credentials.length === 0
                ? isAdmin
                  ? "No credentials in the vault yet"
                  : "No credential sets assigned"
                : `${credentials.length} credential set${
                    credentials.length !== 1 ? "s" : ""
                  }`}
            </p>
          </div>
        </div>

        {credentials.length === 0 ? (
          <p
            className="card-subtitle"
            style={{ textAlign: "center", padding: 20 }}
          >
            {isAdmin
              ? "Create your first credential set above."
              : "Ask an administrator to assign SSH credential sets to your account."}
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
                    {cred.updated_at && (
                      <span className="helper-text" style={{ fontSize: 11 }}>
                        Updated: {new Date(cred.updated_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  {isAdmin && (
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
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
