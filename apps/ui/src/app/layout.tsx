import type { Metadata } from "next";
import "../styles/globals.css";
import { Header } from "@/components/Header";
import { ToastProvider } from "@/components/ToastProvider";

export const metadata: Metadata = {
  title: "Chiptuning / Автосервис — локальный AI приёмщик",
  description: "Локальный AI-ассистент: заявка → черновик сметы → подтверждение оператором.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <div className="app-bg" aria-hidden />
        <ToastProvider>
          <Header />
          {children}
        </ToastProvider>
      </body>
    </html>
  );
}

