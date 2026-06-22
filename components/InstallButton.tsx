"use client";

import { useEffect, useState } from "react";
import type { Palette } from "@/lib/theme";

type BIPEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

// Custom "Install app" button. Uses the captured beforeinstallprompt event on
// Chromium; on iOS Safari (which has no such event) it shows the manual
// Add-to-Home-Screen hint instead. Hides itself once installed.
export function InstallButton({ p }: { p: Palette }) {
  const [deferred, setDeferred] = useState<BIPEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [showIosHint, setShowIosHint] = useState(false);

  useEffect(() => {
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      // iOS
      (navigator as Navigator & { standalone?: boolean }).standalone === true;
    if (standalone) {
      setInstalled(true);
      return;
    }

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BIPEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setDeferred(null);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed) return null;

  async function install() {
    if (deferred) {
      await deferred.prompt();
      const choice = await deferred.userChoice;
      if (choice.outcome === "accepted") setInstalled(true);
      setDeferred(null);
    } else {
      // No native prompt (iOS Safari / not yet eligible) → show the manual hint.
      setShowIosHint((v) => !v);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <button
        onClick={install}
        className="rounded-full px-5 py-1.5 font-bold text-sm"
        style={{ background: p.btn_bg, color: p.btn_text }}
      >
        ⬇ Install app
      </button>
      {showIosHint && (
        <span className="text-xs leading-snug" style={{ color: p.muted }}>
          On iPhone: tap the <b>Share</b> icon, then <b>Add to Home Screen</b>.
        </span>
      )}
    </div>
  );
}
