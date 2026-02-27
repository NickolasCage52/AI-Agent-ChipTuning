"use client";

import { useCallback, useState } from "react";

import { PartsAssistantLayout, type PartsAssistantMsg } from "./PartsAssistantLayout";

const CORE_API_URL = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

export function PartsAssistant() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<PartsAssistantMsg[]>([
    { role: "assistant", text: "Привет! Я помогу подобрать запчасти. Заполните данные авто выше и напишите, что нужно — например: колодки передние, масляный фильтр, ТО или опишите проблему." },
  ]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [brand, setBrand] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState("");
  const [engine, setEngine] = useState("");
  const [mileage, setMileage] = useState("");
  const [vin, setVin] = useState("");

  const getCarContext = useCallback(() => {
    const ctx: Record<string, string | number | null> = {};
    if (brand.trim()) ctx.brand = brand.trim();
    if (model.trim()) ctx.model = model.trim();
    if (year.trim()) ctx.year = year.trim() as unknown as number;
    if (engine.trim()) ctx.engine = engine.trim();
    if (mileage.trim()) ctx.mileage = mileage.trim() as unknown as number;
    if (vin.trim()) ctx.vin = vin.trim();
    return ctx;
  }, [brand, model, year, engine, mileage, vin]);

  const send = useCallback(async (msg: string) => {
    const trimmed = msg.trim();
    if (!trimmed) return;
    setMessages((m) => [...m, { role: "user", text: trimmed }, { role: "assistant", text: "", typing: true }]);
    setText("");
    setLoading(true);
    try {
      const r = await fetch(`${CORE_API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, car_context: getCarContext(), session_id: sessionId }),
      });
      const data = await r.json();
      if (!r.ok) {
        const detail = data?.detail;
        const errMsg = Array.isArray(detail) && detail[0] ? detail[0].msg : detail || r.statusText;
        throw new Error(errMsg || "Ошибка запроса");
      }
      setSessionId(data.session_id);
      setMessages((m) => {
        const withoutTyping = m.filter((x) => !("typing" in x) || !x.typing);
        return [...withoutTyping, { role: "assistant", text: data.summary, chatResponse: data }];
      });
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      setMessages((m) => {
        const withoutTyping = m.filter((x) => !("typing" in x) || !x.typing);
        return [...withoutTyping, { role: "assistant", text: `Ошибка: ${err.message || "Попробуйте позже"}` }];
      });
    } finally {
      setLoading(false);
    }
  }, [sessionId, getCarContext]);

  return (
    <PartsAssistantLayout
      messages={messages}
      text={text}
      loading={loading}
      brand={brand}
      model={model}
      year={year}
      engine={engine}
      mileage={mileage}
      vin={vin}
      onBrandChange={setBrand}
      onModelChange={setModel}
      onYearChange={setYear}
      onEngineChange={setEngine}
      onMileageChange={setMileage}
      onVinChange={setVin}
      onTextChange={setText}
      onSend={send}
    />
  );
}
