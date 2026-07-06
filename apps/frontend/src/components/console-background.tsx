export function ConsoleBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-background"
    >
      <div className="absolute inset-[-44px] grid-backdrop animate-drift opacity-70" />

      <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_-10%,transparent_40%,var(--background)_100%)]" />

      <svg
        className="absolute inset-0 h-full w-full"
        preserveAspectRatio="none"
        viewBox="0 0 1440 900"
        fill="none"
      >
        <path
          d="M-40 720 C 320 560, 620 640, 900 420 S 1360 180, 1520 120"
          className="animate-dash"
          stroke="var(--color-primary)"
          strokeWidth="1"
          strokeOpacity="0.25"
        />
        <path
          d="M-40 300 C 260 360, 540 220, 820 300 S 1280 520, 1520 440"
          className="animate-dash"
          stroke="var(--color-accent)"
          strokeWidth="1"
          strokeOpacity="0.18"
          style={{ animationDuration: "55s" }}
        />
      </svg>

      <div className="absolute -right-40 -top-40 size-[520px] opacity-[0.35]">
        <div className="absolute inset-0 rounded-full border border-primary/15" />
        <div className="absolute inset-[18%] rounded-full border border-primary/10" />
        <div className="absolute inset-[38%] rounded-full border border-primary/10" />
        <div className="absolute inset-[58%] rounded-full border border-primary/10" />
        <div
          className="absolute inset-0 origin-center rounded-full animate-radar"
          style={{
            background:
              "conic-gradient(from 0deg, var(--color-primary) 0deg, transparent 42deg, transparent 360deg)",
            maskImage:
              "radial-gradient(circle, black 0%, black 60%, transparent 62%)",
            WebkitMaskImage:
              "radial-gradient(circle, black 0%, black 60%, transparent 62%)",
            opacity: 0.14,
          }}
        />
      </div>

      <div className="absolute left-[22%] top-[38%] size-1.5 rounded-full bg-accent animate-beacon" />
      <div
        className="absolute left-[68%] top-[64%] size-1.5 rounded-full bg-primary animate-beacon"
        style={{ animationDelay: "0.8s" }}
      />
      <div
        className="absolute left-[46%] top-[18%] size-1 rounded-full bg-primary animate-beacon"
        style={{ animationDelay: "1.6s" }}
      />
    </div>
  );
}
