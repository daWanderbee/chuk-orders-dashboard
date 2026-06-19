"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CHUK_LOGO } from "@/app/assets/logo";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      router.replace(params.get("from") || "/");
      router.refresh();
    } else {
      setError("Wrong password.");
      setBusy(false);
    }
  }

  return (
    <div
      style={{ background: "#942A45" }}
      className="min-h-screen flex flex-col items-center justify-center gap-6 px-4"
    >
      <img
        src={CHUK_LOGO}
        alt="CHUK"
        style={{ height: 54, background: "#FFF2E0", padding: "12px 20px", borderRadius: 14 }}
      />
      <div className="text-[#FFF2E0] font-bold text-lg">Orders Dashboard</div>
      <form onSubmit={submit} className="flex flex-col gap-3 w-full max-w-[320px]">
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Enter password"
          className="rounded-full px-5 py-2.5 outline-none text-center"
          style={{ background: "#FFF2E0", color: "#3A1620" }}
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-full px-5 py-2.5 font-bold disabled:opacity-60"
          style={{ background: "#F3B343", color: "#3A1620" }}
        >
          {busy ? "…" : "Enter"}
        </button>
        {error && <div className="text-center text-[#FFD9D4] text-sm">{error}</div>}
      </form>
    </div>
  );
}
