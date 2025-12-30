import { useState, useEffect } from "react";
import { apiCall } from "./utils/api";

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [activity, setActivity] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("users");
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [availablePrivileges, setAvailablePrivileges] = useState([]);
  const [bulkTemplates, setBulkTemplates] = useState(null);
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    email: "",
    role: "operator",
    privileges: [],
  });

  useEffect(() => {
    loadData();
  }, [activeTab]);

  useEffect(() => {
    loadPrivileges();
  }, []); // Load privileges once on mount

  const loadPrivileges = async () => {
    try {
      const res = await apiCall("admin/privileges");
      if (res.ok) {
        const data = await res.json();
        setAvailablePrivileges(data.privileges || []);
      } else {
        console.error("Failed to load privileges:", res.status, res.statusText);
        // Fallback to default privileges if API fails
        setAvailablePrivileges([
          {
            id: "bulk_operations",
            name: "Bulk Operations",
            description: "Execute bulk device operations",
          },
          {
            id: "router_commands",
            name: "Router Commands",
            description: "Execute router commands",
          },
          {
            id: "view_history",
            name: "View History",
            description: "View saved configs and logs",
          },
          {
            id: "view_backups",
            name: "View Backups",
            description: "View configuration backups",
          },
          {
            id: "manage_reports",
            name: "Manage Reports",
            description: "Manage report schedules",
          },
          {
            id: "manage_credentials",
            name: "Manage Credentials",
            description: "Manage SSH credentials",
          },
          {
            id: "admin_access",
            name: "Admin Access",
            description: "Access admin panel",
          },
        ]);
      }
    } catch (e) {
      console.error("Error loading privileges:", e);
      // Fallback to default privileges
      setAvailablePrivileges([
        {
          id: "bulk_operations",
          name: "Bulk Operations",
          description: "Execute bulk device operations",
        },
        {
          id: "router_commands",
          name: "Router Commands",
          description: "Execute router commands",
        },
        {
          id: "view_history",
          name: "View History",
          description: "View saved configs and logs",
        },
        {
          id: "view_backups",
          name: "View Backups",
          description: "View configuration backups",
        },
        {
          id: "manage_reports",
          name: "Manage Reports",
          description: "Manage report schedules",
        },
        {
          id: "manage_credentials",
          name: "Manage Credentials",
          description: "Manage SSH credentials",
        },
        {
          id: "admin_access",
          name: "Admin Access",
          description: "Access admin panel",
        },
      ]);
    }
  };

  const loadData = async () => {
    try {
      if (activeTab === "users") {
        const res = await apiCall("admin/users");
        if (res.ok) {
          setUsers(await res.json());
        }
      } else if (activeTab === "activity") {
        try {
          const res = await apiCall("admin/activity?limit=500");
          if (res.ok) {
            const activities = await res.json();
            console.log("Activity logs loaded:", activities.length, "entries");
            setActivity(Array.isArray(activities) ? activities : []);
          } else {
            const errorText = await res.text();
            console.error(
              "Failed to load activity log:",
              res.status,
              errorText
            );
            setActivity([]);
          }
        } catch (e) {
          console.error("Error loading activity log:", e);
          setActivity([]);
        }
      } else if (activeTab === "stats") {
        const res = await apiCall("admin/stats");
        if (res.ok) {
          setStats(await res.json());
        }
      } else if (activeTab === "bulkTemplates") {
        const res = await apiCall("admin/bulk-templates");
        if (res.ok) {
          setBulkTemplates(await res.json());
        }
      }
    } catch (e) {
      console.error("Error loading data:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    if (!formData.username.trim() || !formData.password.trim()) {
      alert("Username and password are required");
      return;
    }

    if (formData.privileges.length === 0) {
      alert("Please select at least one privilege");
      return;
    }

    try {
      const fd = new FormData();
      fd.append("username", formData.username.trim());
      fd.append("password", formData.password);
      fd.append("email", formData.email.trim());
      // Use "custom" role when user selects custom privileges, or use the selected role
      const roleToUse = formData.role === "custom" ? "custom" : formData.role;
      fd.append("role", roleToUse);
      fd.append("privileges_json", JSON.stringify(formData.privileges));

      const res = await apiCall("admin/users", {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const error = await res.json();
        alert(`Error: ${error.detail || "Failed to create user"}`);
        return;
      }

      setShowUserForm(false);
      setFormData({ username: "", password: "", email: "", role: "operator" });
      loadData();
    } catch (e) {
      alert(`Error: ${e.toString()}`);
    }
  };

  const handleUpdateUser = async () => {
    if (!editingUser) return;

    try {
      const fd = new FormData();
      if (formData.username !== editingUser.username) {
        fd.append("username", formData.username.trim());
      }
      if (formData.email !== editingUser.email) {
        fd.append("email", formData.email.trim());
      }
      if (formData.role !== editingUser.role) {
        fd.append("role", formData.role);
      }
      if (formData.password.trim()) {
        fd.append("password", formData.password);
      }
      fd.append(
        "active",
        formData.active !== undefined ? formData.active : editingUser.active
      );
      // Always send privileges to allow granular control
      fd.append("privileges_json", JSON.stringify(formData.privileges));

      const res = await apiCall(`admin/users/${editingUser.id}`, {
        method: "PUT",
        body: fd,
      });

      if (!res.ok) {
        const error = await res.json();
        alert(`Error: ${error.detail || "Failed to update user"}`);
        return;
      }

      setEditingUser(null);
      setShowUserForm(false);
      setFormData({
        username: "",
        password: "",
        email: "",
        role: "operator",
        privileges: [],
      });
      loadData();
    } catch (e) {
      alert(`Error: ${e.toString()}`);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Are you sure you want to delete this user?")) return;

    try {
      const res = await apiCall(`admin/users/${userId}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const error = await res.json();
        alert(`Error: ${error.detail || "Failed to delete user"}`);
        return;
      }

      loadData();
    } catch (e) {
      alert(`Error: ${e.toString()}`);
    }
  };

  const startEdit = (user) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      password: "",
      email: user.email || "",
      role: user.role,
      active: user.active,
      privileges: user.privileges || [],
    });
    setShowUserForm(true);
  };

  const cancelEdit = () => {
    setEditingUser(null);
    setShowUserForm(false);
    setFormData({
      username: "",
      password: "",
      email: "",
      role: "operator",
      privileges: [],
    });
  };

  const togglePrivilege = (privilegeId) => {
    setFormData((prev) => {
      const current = prev.privileges || [];
      if (current.includes(privilegeId)) {
        return {
          ...prev,
          privileges: current.filter((p) => p !== privilegeId),
        };
      } else {
        return { ...prev, privileges: [...current, privilegeId] };
      }
    });
  };

  return (
    <>
      <div className="app-main-header">
        <div>
          <h2 className="app-main-title">Administration</h2>
          <p className="app-main-subtitle">
            Manage users, view activity logs, and monitor system statistics.
          </p>
        </div>
        <span className="pill">Admin Only</span>
      </div>

      <div className="card" style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            className={
              "button button--sm" +
              (activeTab === "users" ? " button--primary" : " button--ghost")
            }
            onClick={() => setActiveTab("users")}
          >
            Users
          </button>
          <button
            type="button"
            className={
              "button button--sm" +
              (activeTab === "activity" ? " button--primary" : " button--ghost")
            }
            onClick={() => setActiveTab("activity")}
          >
            Activity Log
          </button>
          <button
            type="button"
            className={
              "button button--sm" +
              (activeTab === "stats" ? " button--primary" : " button--ghost")
            }
            onClick={() => setActiveTab("stats")}
          >
            Statistics
          </button>
          <button
            type="button"
            className={
              "button button--sm" +
              (activeTab === "bulkTemplates"
                ? " button--primary"
                : " button--ghost")
            }
            onClick={() => setActiveTab("bulkTemplates")}
          >
            Bulk Templates
          </button>
        </div>
      </div>

      {activeTab === "users" && (
        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">User Management</h3>
              <p className="card-subtitle">
                Create, edit, and manage user accounts and permissions.
              </p>
            </div>
            <button
              type="button"
              className="button button--primary button--sm"
              onClick={() => {
                setEditingUser(null);
                setFormData({
                  username: "",
                  password: "",
                  email: "",
                  role: "operator",
                  privileges: [],
                });
                setShowUserForm(true);
              }}
            >
              + New User
            </button>
          </div>

          {showUserForm && (
            <div className="card" style={{ marginBottom: 18, padding: 16 }}>
              <h4 className="card-title" style={{ marginBottom: 12 }}>
                {editingUser ? "Edit User" : "Create New User"}
              </h4>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Username *</label>
                  <input
                    className="input"
                    value={formData.username}
                    onChange={(e) =>
                      setFormData({ ...formData, username: e.target.value })
                    }
                    disabled={!!editingUser}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input
                    className="input"
                    type="email"
                    value={formData.email}
                    onChange={(e) =>
                      setFormData({ ...formData, email: e.target.value })
                    }
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">
                    {editingUser
                      ? "New Password (leave blank to keep)"
                      : "Password *"}
                  </label>
                  <input
                    className="input"
                    type="password"
                    value={formData.password}
                    onChange={(e) =>
                      setFormData({ ...formData, password: e.target.value })
                    }
                    required={!editingUser}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Role (for reference)</label>
                  <select
                    className="select"
                    value={formData.role}
                    onChange={(e) =>
                      setFormData({ ...formData, role: e.target.value })
                    }
                  >
                    <option value="admin">Admin</option>
                    <option value="operator">Operator</option>
                    <option value="viewer">Viewer</option>
                    <option value="custom">Custom</option>
                  </select>
                  <p
                    className="card-subtitle"
                    style={{ marginTop: 4, fontSize: 11 }}
                  >
                    Role is for reference only. Actual access is controlled by
                    privileges below.
                  </p>
                </div>

                <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                  <label className="form-label">Page Access Privileges *</label>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(250px, 1fr))",
                      gap: 12,
                      marginTop: 8,
                    }}
                  >
                    {availablePrivileges && availablePrivileges.length > 0 ? (
                      availablePrivileges.map((priv) => (
                        <label
                          key={priv.id}
                          style={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 8,
                            padding: 12,
                            borderRadius: 6,
                            border: "1px solid rgba(148, 163, 184, 0.3)",
                            cursor: "pointer",
                            background: formData.privileges.includes(priv.id)
                              ? "rgba(34, 197, 94, 0.1)"
                              : "transparent",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={formData.privileges.includes(priv.id)}
                            onChange={() => togglePrivilege(priv.id)}
                            style={{ marginTop: 2 }}
                          />
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 500, fontSize: 13 }}>
                              {priv.name}
                            </div>
                            <div
                              style={{
                                fontSize: 11,
                                color: "#9ca3af",
                                marginTop: 2,
                              }}
                            >
                              {priv.description}
                            </div>
                          </div>
                        </label>
                      ))
                    ) : (
                      <div
                        style={{
                          padding: 16,
                          textAlign: "center",
                          color: "#9ca3af",
                        }}
                      >
                        Loading privileges...
                      </div>
                    )}
                  </div>
                  {formData.privileges.length === 0 && (
                    <p
                      style={{
                        marginTop: 8,
                        fontSize: 12,
                        color: "#f59e0b",
                      }}
                    >
                      ⚠ Please select at least one privilege
                    </p>
                  )}
                </div>

                {editingUser && (
                  <div className="form-group">
                    <label className="form-label">
                      <input
                        type="checkbox"
                        checked={formData.active}
                        onChange={(e) =>
                          setFormData({ ...formData, active: e.target.checked })
                        }
                        style={{ marginRight: 8 }}
                      />
                      Active
                    </label>
                  </div>
                )}
              </div>

              <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className="button button--primary"
                  onClick={editingUser ? handleUpdateUser : handleCreateUser}
                >
                  {editingUser ? "Update User" : "Create User"}
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={cancelEdit}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <ul className="list">
            {users.map((user) => (
              <li key={user.id} style={{ marginBottom: 8 }}>
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
                      <strong>{user.username}</strong>
                      <span className="tag">{user.role}</span>
                      {!user.active && (
                        <span className="tag" style={{ background: "#7f1d1d" }}>
                          Inactive
                        </span>
                      )}
                    </div>
                    {user.email && (
                      <p
                        className="card-subtitle"
                        style={{ margin: 0, fontSize: 12 }}
                      >
                        {user.email}
                      </p>
                    )}
                    <div
                      style={{ marginTop: 4, fontSize: 11, color: "#6b7280" }}
                    >
                      Privileges: {user.privileges.join(", ")}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      type="button"
                      className="button button--ghost button--sm"
                      onClick={() => startEdit(user)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="button button--danger button--sm"
                      onClick={() => handleDeleteUser(user.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {activeTab === "activity" && (
        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Activity Log</h3>
              <p className="card-subtitle">
                View recent user activities and system events.
              </p>
            </div>
          </div>

          <div style={{ maxHeight: "70vh", overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr
                  style={{ borderBottom: "1px solid rgba(148, 163, 184, 0.3)" }}
                >
                  <th
                    style={{
                      padding: 8,
                      textAlign: "left",
                      fontSize: 12,
                      color: "#9ca3af",
                    }}
                  >
                    Timestamp
                  </th>
                  <th
                    style={{
                      padding: 8,
                      textAlign: "left",
                      fontSize: 12,
                      color: "#9ca3af",
                    }}
                  >
                    User
                  </th>
                  <th
                    style={{
                      padding: 8,
                      textAlign: "left",
                      fontSize: 12,
                      color: "#9ca3af",
                    }}
                  >
                    Action
                  </th>
                  <th
                    style={{
                      padding: 8,
                      textAlign: "left",
                      fontSize: 12,
                      color: "#9ca3af",
                    }}
                  >
                    Details
                  </th>
                  <th
                    style={{
                      padding: 8,
                      textAlign: "left",
                      fontSize: 12,
                      color: "#9ca3af",
                    }}
                  >
                    Page
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading && activity.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      style={{
                        padding: 40,
                        textAlign: "center",
                        color: "#9ca3af",
                      }}
                    >
                      Loading activity logs...
                    </td>
                  </tr>
                ) : activity && activity.length > 0 ? (
                  activity.map((log, idx) => (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: "1px solid rgba(148, 163, 184, 0.1)",
                      }}
                    >
                      <td style={{ padding: 8, fontSize: 12 }}>
                        {log.timestamp
                          ? new Date(log.timestamp).toLocaleString()
                          : "-"}
                      </td>
                      <td style={{ padding: 8, fontSize: 12 }}>
                        {log.user_id || "-"}
                      </td>
                      <td style={{ padding: 8, fontSize: 12 }}>
                        <span className="tag">{log.action || "-"}</span>
                      </td>
                      <td
                        style={{
                          padding: 8,
                          fontSize: 12,
                          maxWidth: 400,
                          wordBreak: "break-word",
                        }}
                      >
                        {log.details || "-"}
                      </td>
                      <td style={{ padding: 8, fontSize: 12 }}>
                        {log.page || "-"}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan={5}
                      style={{
                        padding: 40,
                        textAlign: "center",
                        color: "#9ca3af",
                      }}
                    >
                      No activity logs found. Activities will appear here as
                      users interact with the system.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {activeTab === "stats" && stats && (
        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Statistics</h3>
              <p className="card-subtitle">System overview and metrics.</p>
            </div>
          </div>

          <div className="form-grid">
            <div className="card" style={{ padding: 16 }}>
              <div
                style={{ fontSize: 24, fontWeight: "bold", marginBottom: 4 }}
              >
                {stats.total_users}
              </div>
              <div className="card-subtitle">Total Users</div>
            </div>
            <div className="card" style={{ padding: 16 }}>
              <div
                style={{ fontSize: 24, fontWeight: "bold", marginBottom: 4 }}
              >
                {stats.active_users}
              </div>
              <div className="card-subtitle">Active Users</div>
            </div>
            <div className="card" style={{ padding: 16 }}>
              <div
                style={{ fontSize: 24, fontWeight: "bold", marginBottom: 4 }}
              >
                {stats.recent_activities_24h}
              </div>
              <div className="card-subtitle">Activities (24h)</div>
            </div>
          </div>
        </section>
      )}

      {activeTab === "bulkTemplates" && bulkTemplates && (
        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Bulk Excel Templates</h3>
              <p className="card-subtitle">
                Define required Excel columns for each bulk operation.
              </p>
            </div>
          </div>

          {Object.entries(bulkTemplates).map(([operation, columns]) => (
            <div key={operation} style={{ marginBottom: 20 }}>
              <h4 style={{ textTransform: "capitalize", marginBottom: 8 }}>
                {operation} operation
              </h4>

              {columns.map((col, idx) => (
                <div
                  key={idx}
                  style={{ display: "flex", gap: 8, marginBottom: 6 }}
                >
                  <input
                    className="input"
                    value={col}
                    onChange={(e) => {
                      const copy = { ...bulkTemplates };
                      copy[operation][idx] = e.target.value;
                      setBulkTemplates(copy);
                    }}
                  />
                  <button
                    className="button button--danger button--sm"
                    type="button"
                    onClick={() => {
                      const copy = { ...bulkTemplates };
                      copy[operation].splice(idx, 1);
                      setBulkTemplates(copy);
                    }}
                  >
                    ✕
                  </button>
                </div>
              ))}

              <button
                className="button button--ghost button--sm"
                type="button"
                onClick={() => {
                  const copy = { ...bulkTemplates };
                  copy[operation].push("NewColumn");
                  setBulkTemplates(copy);
                }}
              >
                + Add column
              </button>
            </div>
          ))}

          <div style={{ marginTop: 16 }}>
            <button
              className="button button--primary"
              type="button"
              onClick={async () => {
                const res = await apiCall("admin/bulk-templates", {
                  method: "PUT",
                  body: JSON.stringify(bulkTemplates),
                });

                if (res.ok) {
                  alert("Templates saved successfully");
                } else {
                  alert("Failed to save templates");
                }
              }}
            >
              💾 Save templates
            </button>
          </div>
        </section>
      )}
    </>
  );
}
