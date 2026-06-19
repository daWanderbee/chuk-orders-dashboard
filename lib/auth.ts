// Password-gate helpers. Works in both the Edge middleware and Node route
// handlers (uses Web Crypto, available globally in both runtimes).
export const AUTH_COOKIE = "chuk_auth";

// Deterministic token derived from the configured password, so the cookie
// never stores the raw password.
export async function authToken(password: string): Promise<string> {
  const data = new TextEncoder().encode("chuk:" + password);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function expectedToken(): Promise<string | null> {
  const pw = process.env.APP_PASSWORD;
  if (!pw) return null; // no password configured → gate is open
  return authToken(pw);
}
