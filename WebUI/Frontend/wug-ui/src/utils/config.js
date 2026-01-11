// Centralized API configuration
// Use api or wug.automation as the API host
const API_BASE_URL = "http://wug.automation:8000";

export const API_URL = API_BASE_URL;

// Helper function to build full API URLs
export function apiUrl(path) {
  // Remove leading slash if present to avoid double slashes
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${API_BASE_URL}/${cleanPath}`;
}
