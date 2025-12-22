import { useState } from "react";
import { setToken, setUser } from "./utils/auth";
import { apiUrl } from "./utils/config";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // Validate inputs
    if (!username.trim() || !password.trim()) {
      setError("Please enter both username and password");
      setLoading(false);
      return;
    }

    try {
      // Use URLSearchParams instead of FormData for simple form fields
      // FastAPI Form() accepts both multipart/form-data and application/x-www-form-urlencoded
      const formData = new URLSearchParams();
      formData.append("username", username.trim());
      formData.append("password", password);

      const res = await fetch(apiUrl("auth/login"), {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      });

      console.log("Response status:", res.status);
      console.log("Response ok:", res.ok);

      // Get response text first to handle both JSON and text errors
      const responseText = await res.text();

      let data;
      try {
        data = JSON.parse(responseText);
      } catch (e) {
        setError(`Server error: ${responseText || res.statusText}`);
        setLoading(false);
        return;
      }

      if (!res.ok) {
        setError(data.detail || "Login failed");
        setLoading(false);
        return;
      }

      setToken(data.access_token);
      setUser(data.user);
      onLogin(data.user);
    } catch (e) {
      console.error("Login error:", e);
      setError(
        `Network error: ${e.message}. Please check if the backend is running.`
      );
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "radial-gradient(circle at top, #1f2937 0, #020617 55%)",
        padding: 20,
      }}
    >
      <div className="card" style={{ maxWidth: 400, width: "100%" }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">WhatsUp Automation Console</h2>
            <p className="card-subtitle">Please sign in to continue</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              className="input"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              className="input"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          {error && (
            <div
              style={{
                padding: 12,
                borderRadius: 8,
                background: "rgba(248, 113, 113, 0.1)",
                border: "1px solid rgba(248, 113, 113, 0.5)",
                color: "#fecaca",
                fontSize: 13,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          <div style={{ marginTop: 20 }}>
            <button
              type="submit"
              className="button button--primary"
              disabled={loading}
              style={{ width: "100%" }}
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </div>
        </form>

        <div
          style={{
            marginTop: 20,
            fontSize: 12,
            color: "#9ca3af",
            textAlign: "center",
          }}
        >
          Default credentials: admin / admin
        </div>
      </div>
    </div>
  );
}
