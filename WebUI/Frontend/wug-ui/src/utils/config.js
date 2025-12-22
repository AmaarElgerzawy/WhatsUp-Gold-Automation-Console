// Centralized API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || "http://api:8000";

export const API_URL = API_BASE_URL;

// Helper function to build full API URLs
export function apiUrl(path) {
  // Remove leading slash if present to avoid double slashes
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${API_BASE_URL}/${cleanPath}`;
}
