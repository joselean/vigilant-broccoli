import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t border-white/10 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-white/50 md:flex-row">
        <Logo />
        <p>© {new Date().getFullYear()} ULTIMA HOST. Все права защищены.</p>
      </div>
    </footer>
  );
}
