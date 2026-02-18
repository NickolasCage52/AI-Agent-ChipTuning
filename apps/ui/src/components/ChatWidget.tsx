"use client";

import { useMemo, useState } from "react";
import { useToast } from "@/components/ToastProvider";

const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8001";
const PAGES_PREVIEW = process.env.NEXT_PUBLIC_PAGES_PREVIEW === "true";
const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL || "https://github.com";

type AgentCitation = { title: string; section?: string | null };
type EstimateUI = {
  jobs: { name: string; qty?: number; unit_price?: number | null; total?: number | null }[];
  parts: { economy: any[]; optimum: any[]; oem: any[] };
  totals: { jobs_total?: number | null; parts_total?: number | null; total?: number | null };
  requires_approval: boolean;
};
type AgentUiResponse = {
  answer_text: string;
  questions: string[];
  estimate_ui?: EstimateUI | null;
  next_step: string;
  citations: AgentCitation[];
};

type Msg =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; response?: AgentUiResponse | null; typing?: boolean };

function TypingBubble() {
  return (
    <div className="typing-dots" aria-label="Ассистент печатает">
      <span />
      <span />
      <span />
    </div>
  );
}

export function ChatWidget() {
  const toast = useToast();
  const [leadId, setLeadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", text: "Здравствуйте! Чем помочь: ТО, подбор запчастей или диагностика по симптому?" },
  ]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  const quick = useMemo(
    () => [
      { label: "ТО", message: "Нужно ТО" },
      { label: "Запчасти", message: "Нужны запчасти" },
      { label: "Проблема", message: "Стук справа при повороте" },
    ],
    []
  );

  async function send(msg: string) {
    const trimmed = msg.trim();
    if (!trimmed) return;
    if (PAGES_PREVIEW) {
      toast.info("Это превью интерфейса на GitHub Pages. Для полного демо запустите проект локально.", "Pages preview");
      setMessages((m) => [
        ...m,
        { role: "user", text: trimmed },
        {
          role: "assistant",
          text: `Для полного демо нужен локальный запуск: docker compose up --build\nREADME: ${REPO_URL}`,
        },
      ]);
      return;
    }
    setMessages((m) => [...m, { role: "user", text: trimmed }, { role: "assistant", text: "", typing: true }]);
    setText("");
    setLoading(true);
    try {
      const r = await fetch(`${AGENT_URL}/api/agent/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "web", lead_id: leadId, message: trimmed }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.detail || r.statusText);
      setLeadId(data.lead_id);
      const resp: AgentUiResponse | null = data?.response || null;
      setMessages((m) => {
        const withoutTyping = m.filter((x) => !("typing" in x) || !x.typing);
        return [...withoutTyping, { role: "assistant", text: resp?.answer_text || data.answer, response: resp }];
      });
    } catch (e: any) {
      setMessages((m) => m.filter((x) => !("typing" in x) || !x.typing));
      toast.error("Что-то пошло не так, попробуйте ещё раз.", "Ошибка");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card glass">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-semibold">AI‑приёмщик</div>
        <div className="text-xs" style={{ color: "var(--muted)" }}>{leadId ? "заявка создана" : "готов помочь"}</div>
      </div>
      <div className="mb-3 flex flex-wrap gap-2">
        {quick.map((q) => (
          <button
            key={q.label}
            className="rounded-full border px-3 py-1 text-xs"
            style={{ borderColor: "var(--border)", color: "var(--muted)", background: "rgba(255,255,255,0.02)" }}
            onClick={() => send(q.message)}
            disabled={loading}
          >
            {q.label}
          </button>
        ))}
      </div>
      <div className="h-72 overflow-auto rounded-xl border p-3" style={{ borderColor: "var(--border)" }}>
        <div className="flex flex-col gap-3">
          {messages.map((m, idx) => (
            <div key={idx} className={m.role === "user" ? "self-end" : "self-start"}>
              <div
                className="max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm"
                style={{
                  background: m.role === "user" ? "rgba(225,29,46,0.15)" : "rgba(255,255,255,0.04)",
                  border: `1px solid var(--border)`,
                }}
              >
                {"typing" in m && m.typing ? <TypingBubble /> : m.text}
                {"response" in m && m.response?.next_step ? (
                  <div className="mt-2 text-xs" style={{ color: "var(--muted)" }}>
                    Следующий шаг: <span className="text-fg">{m.response.next_step}</span>
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <input
          className="input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Напишите сообщение…"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(text);
            }
          }}
        />
        <button className="btn-primary" disabled={loading} onClick={() => send(text)}>
          {loading ? "..." : "Отправить"}
        </button>
      </div>
    </div>
  );
}

