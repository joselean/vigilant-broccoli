import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "cyrillic"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "ULTIMA HOST — надёжный VDS-хостинг на базе Hetzner",
  description:
    "VDS-серверы с NVMe-дисками, защитой от DDoS и локациями по всему миру. Автоматическое развёртывание после оплаты через сайт или Telegram-бота.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={inter.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
