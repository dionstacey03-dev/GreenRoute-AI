const API_BASE = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");

export async function authenticatedApiRequest(path, getToken, options = {}) {
  if (!API_BASE) {
    throw new Error("API URL is not configured. Set VITE_API_URL for this deployment.");
  }

  const token = await getToken();
  if (!token) {
    throw new Error("Your sign-in session has expired. Please sign in again.");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });

  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : `GreenRoute API returned ${response.status}.`;
    throw new Error(detail);
  }
  return data;
}
