import { DemoClient } from "@/components/DemoClient";

export default function DemoPage() {
  return (
    <main className="container-page py-10">
      <div className="mb-6">
        <div className="text-2xl font-semibold">Demo • Chat → lead → estimate → logs</div>
        <div className="text-sm" style={{ color: "var(--muted)" }}>
          Локальный режим: без Telegram, без внешних LLM, все ответы детерминированы и делаются через tools.
        </div>
      </div>
      <DemoClient />
    </main>
  );
}

