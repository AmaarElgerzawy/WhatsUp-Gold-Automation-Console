// Centralized API configuration
// Use api or wug.automation as the API host
import { API_BASE_URL, apiUrl as buildApiUrl } from "./constants";

export const API_URL = API_BASE_URL;

// Helper function to build full API URLs
export function apiUrl(path) {
  return buildApiUrl(path);
}
