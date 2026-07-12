import Image from "next/image";
import Link from "next/link";
import heroBanner from "../public/images/hero-banner.jpg";

export function Hero() {
  return (
    <section className="mx-auto max-w-6xl px-6 pt-12 md:pt-20">
      <h1 className="sr-only">Надёжный хостинг VDS от ULTIMA HOST для ваших проектов</h1>
      <Link
        href="/tariffs"
        className="group relative block overflow-hidden rounded-2xl border border-white/10 shadow-glow transition hover:border-white/30"
      >
        <Image
          src={heroBanner}
          alt="ULTIMA HOST — надёжный хостинг для ваших проектов. NVMe скорость, защита от DDoS, серверы по всему миру."
          priority
          className="h-auto w-full"
          sizes="(min-width: 1280px) 1152px, 100vw"
        />
      </Link>
    </section>
  );
}
