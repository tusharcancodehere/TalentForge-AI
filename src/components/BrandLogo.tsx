import { motion } from "framer-motion";

export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="inline-flex items-center gap-3"
    >
      <motion.span
        whileHover={{ rotate: -6, scale: 1.06 }}
        transition={{ type: "spring", stiffness: 380, damping: 18 }}
        className="h-8 w-8 rounded-xl flex items-center justify-center"
        style={{
          background:
            "linear-gradient(135deg, var(--accent-glow), var(--accent-glow-2))",
          boxShadow:
            "0 10px 28px -10px color-mix(in oklab, var(--accent-glow) 75%, transparent)",
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M4 15.5L8.5 11L12 14.5L20 6.5"
            stroke="oklch(0.13 0.025 270)"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M15 6.5H20V11.5"
            stroke="oklch(0.13 0.025 270)"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </motion.span>
      <div className="leading-tight">
        <p className="brand-wordmark">
          Talent<span style={{ color: "var(--accent-glow)" }}>Forge</span> AI
        </p>
        {!compact && (
          <p className="text-[10px] uppercase tracking-[0.16em] opacity-60">
            Portfolio Intelligence
          </p>
        )}
      </div>
    </motion.div>
  );
}
