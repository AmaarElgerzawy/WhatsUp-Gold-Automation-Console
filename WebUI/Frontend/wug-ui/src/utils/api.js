import { getAuthHeaders } from "./auth";
import { apiUrl } from "./config";

/**
 * Helper function to make authenticated API calls
 * @param {string} path - API path (e.g., "auth/login" or "/auth/login")
 * @param {object} options - Fetch options
 */
export async function apiCall(path, options = {}) {
  // Build full URL from path
  const url = path.startsWith("http") ? path : apiUrl(path);
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  // If body is FormData, don't set Content-Type (browser will set it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include"
  });

  // If unauthorized, clear auth and redirect to login
  if (response.status === 401) {
    localStorage.removeItem("wug_auth_token");
    localStorage.removeItem("wug_user");
    window.location.reload();
    return response;
  }

  return response;
}
