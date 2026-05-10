import { motion } from "framer-motion";
import { ArrowLeft, Github, MapPin, Link2 } from "lucide-react";
import { ProjectCard, type Project } from "./ProjectCard";

const MOCK_TECH = [
  "TypeScript",
  "React",
  "Node.js",
  "Python",
  "Rust",
  "Go",
  "PostgreSQL",
  "Docker",
  "GraphQL",
  "TailwindCSS",
];

const MOCK_PROJECTS: Project[] = [
  {
    title: "neon-cli",
    description: "Blazing-fast terminal toolkit for managing cloud deploys with a single command.",
    tags: ["Rust", "TUI"],
    stars: 1240,
    forks: 88,
  },
  {
    title: "prism-ui",
    description: "Glassmorphic React component library with built-in theming and animations.",
    tags: ["React", "TypeScript"],
    stars: 3420,
    forks: 210,
  },
  {
    title: "loom-server",
    description: "Self-hosted realtime collaboration server with CRDT-based sync.",
    tags: ["Go", "WebSocket"],
    stars: 890,
    forks: 54,
  },
  {
    title: "ember-ml",
    description: "Lightweight inference engine for running LLMs on edge devices.",
    tags: ["Python", "CUDA"],
    stars: 2105,
    forks: 142,
  },
  {
    title: "atlas-graph",
    description: "Interactive dependency visualizer for monorepos and microservices.",
    tags: ["TypeScript", "D3"],
    stars: 678,
    forks: 32,
  },
  {
    title: "halo-auth",
    description: "Drop-in authentication with passkeys, OAuth, and magic links.",
    tags: ["Node.js", "PostgreSQL"],
    stars: 1560,
    forks: 96,
  },
];

export function Dashboard({ username, onBack }: { username: string; onBack: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="w-full max-w-6xl mx-auto"
    >
      <button
        onClick={onBack}
        className="font-mono text-xs inline-flex items-center gap-2 opacity-70 hover:opacity-100 mb-6 transition-opacity"
      >
        <ArrowLeft className="h-4 w-4" /> back
      </button>

      {/* Profile */}
      <div className="glass rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-center sm:items-start gap-6">
        <div
          className="h-24 w-24 rounded-full shrink-0 flex items-center justify-center text-3xl font-bold"
          style={{
            background:
              "linear-gradient(135deg, var(--accent-glow), var(--accent-glow-2))",
            color: "oklch(0.13 0.025 270)",
          }}
        >
          {username.charAt(0).toUpperCase()}
        </div>
        <div className="flex-1 text-center sm:text-left">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              {username}
            </h2>
            <span className="font-mono text-xs opacity-50">@{username}</span>
          </div>
          <p className="mt-2 opacity-70 max-w-xl text-sm sm:text-base">
            Full-stack engineer crafting tools that make developers faster.
            Believer in clean APIs and dark mode.
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-center sm:justify-start gap-4 text-xs font-mono opacity-60">
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5" /> San Francisco
            </span>
            <a className="inline-flex items-center gap-1.5 hover:opacity-100" href="#">
              <Link2 className="h-3.5 w-3.5" /> {username}.dev
            </a>
            <a
              className="inline-flex items-center gap-1.5 hover:opacity-100"
              href={`https://github.com/${username}`}
              target="_blank"
              rel="noreferrer"
            >
              <Github className="h-3.5 w-3.5" /> github
            </a>
          </div>
        </div>
      </div>

      {/* Tech */}
      <section className="mt-8">
        <h3 className="font-mono text-xs uppercase tracking-widest opacity-60 mb-4 px-1">
          // tech.stack
        </h3>
        <div className="glass rounded-2xl p-5 flex flex-wrap items-center justify-center gap-3 sm:gap-4">
          {MOCK_TECH.map((t, i) => (
            <motion.span
              key={t}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.03 * i }}
              className="font-mono text-xs sm:text-sm px-3 py-1.5 rounded-lg glass"
              style={{
                color: "var(--accent-glow)",
              }}
            >
              {t}
            </motion.span>
          ))}
        </div>
      </section>

      {/* Projects */}
      <section className="mt-10">
        <h3 className="font-mono text-xs uppercase tracking-widest opacity-60 mb-4 px-1">
          // featured.projects
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {MOCK_PROJECTS.map((p, i) => (
            <ProjectCard key={p.title} project={p} index={i} />
          ))}
        </div>
      </section>

      <p className="text-center text-xs font-mono opacity-40 mt-12">
        generated with ♥ — connect a backend to wire real GitHub data
      </p>
    </motion.div>
  );
}