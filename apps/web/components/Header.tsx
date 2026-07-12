import Link from "next/link";
import { Logo } from "./Logo";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-8 text-sm text-white/70 md:flex">
          <Link href="/tariffs" className="hover:text-white">
            Тарифы
          </Link>
          <Link href="/#features" className="hover:text-white">
            Преимущества
          </Link>
          <Link href="/#faq" className="hover:text-white">
            FAQ
          </Link>
        </nav>
        <Link
          href="/tariffs"
          className="rounded-lg border border-white/20 px-5 py-2 text-sm font-medium transition hover:border-white/50 hover:shadow-glow"
        >
          Начать →
        </Link>
      </div>
    </header>
  );
}
