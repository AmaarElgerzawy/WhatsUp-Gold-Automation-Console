import { useState } from "react";
import { setToken, setUser } from "./utils/auth";
import { apiUrl } from "./utils/config";
import {
  ENDPOINTS,
  FORM_FIELDS,
  COLORS,
  SPACING,
  STATUS_MESSAGES,
  ERROR_MESSAGES,
  UI_LABELS,
  CONTENT_TYPES,
} from "./utils/constants";

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
      setError(ERROR_MESSAGES.NO_USERNAME_PASSWORD);
      setLoading(false);
      return;
    }

    try {
      // Use URLSearchParams instead of FormData for simple form fields
      // FastAPI Form() accepts both multipart/form-data and application/x-www-form-urlencoded
      const formData = new URLSearchParams();
      formData.append(FORM_FIELDS.USERNAME, username.trim());
      formData.append(FORM_FIELDS.PASSWORD, password);

      const res = await fetch(apiUrl(ENDPOINTS.AUTH_LOGIN), {
        method: "POST",
        headers: {
          "Content-Type": CONTENT_TYPES.FORM_URLENCODED,
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
        setError(data.detail || ERROR_MESSAGES.LOGIN_FAILED);
        setLoading(false);
        return;
      }

      setToken(data.access_token);
      setUser(data.user);
      onLogin(data.user);
    } catch (e) {
      console.error("Login error:", e);
      setError(
        `${ERROR_MESSAGES.NETWORK_ERROR}: ${e.message}. Please check if the backend is running.`
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
        background: `radial-gradient(circle at top, ${COLORS.BG_GRADIENT_START} 0, ${COLORS.BG_GRADIENT_END} 55%)`,
        padding: SPACING.MD,
      }}
    >
      <div className="card" style={{ maxWidth: 400, width: "100%" }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">{UI_LABELS.CONSOLE_TITLE}</h2>
            <p className="card-subtitle">{UI_LABELS.SIGN_IN_TO_CONTINUE}</p>
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
                padding: SPACING.MD,
                borderRadius: 8,
                background: COLORS.ERROR_BG,
                border: `1px solid ${COLORS.ERROR_BORDER}`,
                color: COLORS.ERROR_TEXT,
                fontSize: 13,
                marginBottom: SPACING.LG,
              }}
            >
              {error}
            </div>
          )}

          <div style={{ marginTop: SPACING.LG }}>
            <button
              type="submit"
              className="button button--primary"
              disabled={loading}
              style={{ width: "100%" }}
            >
              {loading
                ? STATUS_MESSAGES.SIGNING_IN_LABEL
                : STATUS_MESSAGES.SIGN_IN_LABEL}
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
