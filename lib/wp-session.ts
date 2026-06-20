// Server-only: maintains an authenticated WordPress session so we can fetch
// the APIFW invoice PDF (its endpoint gates on is_user_logged_in() +
// manage_woocommerce — no nonce, no access_key, no REST route).
//
// Logs in to wp-login.php with WP_LOGIN_USER / WP_LOGIN_PASS, captures the
// wordpress_logged_in_* / wordpress_sec_* cookies, and caches them in module
// memory (reused across warm invocations). On a 302-to-login the cache is
// dropped and a re-login is attempted once.
import "server-only";

const WP_BASE = (process.env.WP_BASE || "https://chuk.in").replace(/\/$/, "");

let cachedCookie: string | null = null;
let cachedAt = 0;
const COOKIE_TTL_MS = 6 * 60 * 60 * 1000; // re-login every 6h regardless

function parseCookies(setCookies: string[]): string {
  // keep only the WP auth cookies, as "name=value; name=value"
  const wanted = /^(wordpress_logged_in_|wordpress_sec_|wordpress_[0-9a-f]{32})/i;
  const jar: Record<string, string> = {};
  for (const sc of setCookies) {
    const first = sc.split(";")[0];
    const eq = first.indexOf("=");
    if (eq < 0) continue;
    const name = first.slice(0, eq).trim();
    const value = first.slice(eq + 1).trim();
    if (wanted.test(name)) jar[name] = value;
  }
  return Object.entries(jar).map(([k, v]) => `${k}=${v}`).join("; ");
}

async function login(): Promise<string | null> {
  const user = process.env.WP_LOGIN_USER;
  const pass = process.env.WP_LOGIN_PASS;
  if (!user || !pass) return null;

  const body = new URLSearchParams({
    log: user,
    pwd: pass,
    "wp-submit": "Log In",
    redirect_to: `${WP_BASE}/wp-admin/`,
    testcookie: "1",
    rememberme: "forever",
  });

  const res = await fetch(`${WP_BASE}/wp-login.php`, {
    method: "POST",
    body,
    redirect: "manual",
    cache: "no-store",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      // WP refuses login unless the test cookie is present.
      Cookie: "wordpress_test_cookie=WP%20Cookie%20check",
    },
  });

  const setCookies = res.headers.getSetCookie?.() ?? [];
  const cookie = parseCookies(setCookies);
  if (!cookie.includes("wordpress_logged_in_")) {
    return null; // bad creds / login failed
  }
  cachedCookie = cookie;
  cachedAt = Date.now();
  return cookie;
}

async function getCookie(force = false): Promise<string | null> {
  if (!force && cachedCookie && Date.now() - cachedAt < COOKIE_TTL_MS) {
    return cachedCookie;
  }
  return login();
}

export type WpFetchResult =
  | { ok: true; body: ArrayBuffer; contentType: string }
  | { ok: false; status: number; error: string };

// Fetch a logged-in WordPress URL, retrying once after re-login if the session
// has expired (endpoint 302s to wp-login).
export async function wpFetch(url: string): Promise<WpFetchResult> {
  if (!process.env.WP_LOGIN_USER || !process.env.WP_LOGIN_PASS) {
    return { ok: false, status: 503, error: "WP_LOGIN_USER / WP_LOGIN_PASS not set" };
  }

  for (let attempt = 0; attempt < 2; attempt++) {
    const cookie = await getCookie(attempt === 1);
    if (!cookie) return { ok: false, status: 502, error: "WordPress login failed" };

    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 50_000);
    try {
      const res = await fetch(url, {
        headers: { Cookie: cookie },
        redirect: "manual",
        cache: "no-store",
        signal: ctrl.signal,
      });
      // expired session → bounced to login; drop cache and retry once
      if (res.status >= 300 && res.status < 400) {
        cachedCookie = null;
        continue;
      }
      if (!res.ok) {
        return { ok: false, status: 502, error: `invoice source returned ${res.status}` };
      }
      const contentType = res.headers.get("content-type") || "";
      if (!/pdf|octet-stream/i.test(contentType)) {
        return { ok: false, status: 502, error: "endpoint did not return a PDF (auth/config issue)" };
      }
      return { ok: true, body: await res.arrayBuffer(), contentType };
    } catch {
      return { ok: false, status: 502, error: "invoice fetch failed" };
    } finally {
      clearTimeout(t);
    }
  }
  return { ok: false, status: 502, error: "WordPress session could not be established" };
}
