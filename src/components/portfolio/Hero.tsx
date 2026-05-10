import { Github, Sparkles, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

export function Hero({ onGenerate }: { onGenerate: (username: string) => void }) {
  const [username, setUsername] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim()) onGenerate(username.trim());
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="w-full max-w-2xl mx-auto"
    >
      <div className="glass rounded-3xl p-8 sm:p-12 text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass font-mono text-xs mb-6"
        >
          <Sparkles className="h-3 w-3" style={{ color: "var(--accent-glow)" }} />
          <span className="opacity-80">v1.0 — zero config</span>
        </motion.div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-[1.05] text-glow">
          Deploy Your Dev Portfolio
          <br />
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                "linear-gradient(120deg, var(--accent-glow), var(--accent-glow-2))",
            }}
          >
            in 60 Seconds.
          </span>
        </h1>

        <p className="mt-5 text-base sm:text-lg opacity-70 max-w-md mx-auto">
          Drop your GitHub username. We'll do the rest — projects, stack,
          everything beautifully arranged.
        </p>

        <form onSubmit={submit} className="mt-8 flex flex-col sm:flex-row gap-3">
          <div className="glass glow-ring flex items-center gap-3 rounded-2xl px-4 h-14 flex-1 transition-shadow">
            <Github className="h-5 w-5 opacity-70 shrink-0" />
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="github-username"
              className="font-mono bg-transparent outline-none w-full text-sm sm:text-base placeholder:opacity-40"
            />
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.97 }}
            type="submit"
            className="font-mono h-14 px-7 rounded-2xl text-sm font-semibold relative overflow-hidden"
            style={{
              background:
                "linear-gradient(120deg, var(--accent-glow), var(--accent-glow-2))",
              color: "oklch(0.13 0.025 270)",
              boxShadow:
                "0 10px 40px -10px color-mix(in oklab, var(--accent-glow) 70%, transparent)",
            }}
          >
            <span className="inline-flex items-center gap-2">
              Generate <ArrowRight className="h-4 w-4" />
            </span>
          </motion.button>
        </form>

        <div className="mt-6 flex items-center justify-center gap-4 text-xs font-mono opacity-50">
          <span>$ portfolio --user octocat</span>
        </div>
      </div>
    </motion.div>
  );
}