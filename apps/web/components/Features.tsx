const features = [
  {
    icon: "⚡",
    title: "NVMe скорость",
    description: "Диски NVMe на всех тарифах — быстрый отклик и высокая скорость чтения/записи.",
  },
  {
    icon: "🛡",
    title: "Защита от DDoS",
    description: "Встроенная защита от DDoS-атак на уровне сети Hetzner Cloud.",
  },
  {
    icon: "🌐",
    title: "Серверы по всему миру",
    description: "Дата-центры в Германии, Финляндии и США — выбирайте ближайшую локацию.",
  },
  {
    icon: "⏱",
    title: "Мгновенное развёртывание",
    description: "Сервер создаётся автоматически сразу после оплаты — без ожидания менеджера.",
  },
];

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-6 py-20">
      <h2 className="text-2xl font-semibold md:text-3xl">Почему выбирают ULTIMA HOST</h2>
      <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-xl border border-white/10 bg-white/[0.02] p-6 transition hover:border-white/25 hover:bg-white/[0.04]"
          >
            <div className="text-2xl">{f.icon}</div>
            <h3 className="mt-4 font-medium">{f.title}</h3>
            <p className="mt-2 text-sm text-white/60">{f.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
