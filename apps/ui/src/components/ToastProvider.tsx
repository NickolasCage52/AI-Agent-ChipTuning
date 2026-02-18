"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

type ToastKind = "info" | "success" | "error";
type Toast = { id: string; kind: ToastKind; title?: string; message: string };

type ToastApi = {
  push: (t: Omit<Toast, "id">) => void;
  info: (message: string, title?: string) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
};

const ToastContext = createContext<ToastApi | null>(null);

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

function kindStyle(kind: ToastKind) {
  if (kind === "success") return { border: "rgba(82,255,168,0.35)", bg: "rgba(82,255,168,0.08)" };
  if (kind === "error") return { border: "rgba(225,29,46,0.35)", bg: "rgba(225,29,46,0.10)" };
  return { border: "var(--border)", bg: "rgba(255,255,255,0.04)" };
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((t: Omit<Toast, "id">) => {
    const toast: Toast = { id: uid(), ...t };
    setToasts((cur) => [toast, ...cur].slice(0, 4));
    window.setTimeout(() => {
      setToasts((cur) => cur.filter((x) => x.id !== toast.id));
    }, 4500);
  }, []);

  const api: ToastApi = useMemo(
    () => ({
      push,
      info: (message, title) => push({ kind: "info", message, title }),
      success: (message, title) => push({ kind: "success", message, title }),
      error: (message, title) => push({ kind: "error", message, title }),
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 w-[92vw] max-w-sm space-y-2">
        {toasts.map((t) => {
          const s = kindStyle(t.kind);
          return (
            <div
              key={t.id}
              className="pointer-events-auto rounded-2xl border p-4 text-sm shadow-soft"
              style={{ borderColor: s.border, background: s.bg, backdropFilter: "blur(10px)" }}
            >
              {t.title ? <div className="font-semibold">{t.title}</div> : null}
              <div style={{ color: "var(--muted)" }}>{t.message}</div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

