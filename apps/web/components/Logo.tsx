export function Logo({ className }: { className?: string }) {
  return (
    <div className={`flex items-center gap-3 ${className ?? ""}`}>
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M16 1L29 6V15C29 22.5 23.5 28.5 16 31C8.5 28.5 3 22.5 3 15V6L16 1Z"
          stroke="white"
          strokeWidth="1.5"
        />
        <path d="M11 10V18C11 20.7614 13.2386 23 16 23C18.7614 23 21 20.7614 21 18V10" stroke="white" strokeWidth="1.5" />
        <path d="M11 10H21" stroke="white" strokeWidth="1.5" />
      </svg>
      <span className="font-semibold tracking-widest text-lg leading-none">
        ULTIMA
        <span className="block text-[10px] font-normal tracking-[0.35em] text-white/60">HOST</span>
      </span>
    </div>
  );
}
