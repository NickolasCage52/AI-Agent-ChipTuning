import { ChatWidget } from "@/components/ChatWidget";

export default function WidgetPage() {
  return (
    <main className="container-page py-10">
      <div className="mb-6">
        <div className="text-2xl font-semibold">Чат</div>
        <div className="text-sm" style={{ color: "var(--muted)" }}>
          Опишите запрос — я соберу детали и подготовлю предварительный расчёт.
        </div>
      </div>
      <ChatWidget />
    </main>
  );
}

