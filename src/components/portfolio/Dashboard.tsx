import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Github, MapPin, Link2, Download, Loader2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { ProjectCard, type Project } from "./ProjectCard";
import type { GitHubProfile, GitHubRepo } from "@/lib/github";

export function Dashboard({
  profile,
  repos,
  onBack,
}: {
  profile: GitHubProfile;
  repos: GitHubRepo[];
  onBack: () => void;
}) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const progressTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (progressTimer.current) clearInterval(progressTimer.current);
    };
  }, []);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    setProgress(4);
    // simulated progress stream — eases toward 90% while we wait
    if (progressTimer.current) clearInterval(progressTimer.current);
    progressTimer.current = setInterval(() => {
      setProgress((p) => (p < 90 ? p + Math.max(1, (92 - p) * 0.08) : p));
    }, 180);
    const toastId = toast.loading("Generating your CV…", {
      description: `compiling resume for @${profile.login}`,
    });
    try {
      const res = await fetch(`http://localhost:8000/api/cv/${profile.login}`);
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setProgress(100);
      toast.success("CV ready", {
        id: toastId,
        description: "resume.pdf downloaded successfully",
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Download failed";
      setDownloadError(msg);
      toast.error("Export failed", { id: toastId, description: msg });
    } finally {
      if (progressTimer.current) {
        clearInterval(progressTimer.current);
        progressTimer.current = null;
      }
      setDownloading(false);
      setTimeout(() => setProgress(0), 600);
    }
  };

  const projects: Project[] = repos.map((r) => ({
    title: r.name,
    description: r.description ?? "No description provided.",
    tags: r.language ? [r.language] : [],
    stars: r.stargazers_count,
    forks: r.forks_count,
    url: r.html_url,
  }));

  const techSet = Array.from(
    new Set(repos.map((r) => r.language).filter((l): l is string => Boolean(l))),
  );

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
        <img
          src={profile.avatar_url}
          alt={`${profile.login} avatar`}
          className="h-24 w-24 rounded-full shrink-0 object-cover"
          style={{
            boxShadow:
              "0 0 0 2px color-mix(in oklab, var(--accent-glow) 50%, transparent)",
          }}
        />
        <div className="flex-1 text-center sm:text-left">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              {profile.name ?? profile.login}
            </h2>
            <span className="font-mono text-xs opacity-50">@{profile.login}</span>
          </div>
          {profile.bio && (
            <p className="mt-2 opacity-70 max-w-xl text-sm sm:text-base">
              {profile.bio}
            </p>
          )}
          <div className="mt-3 flex flex-wrap items-center justify-center sm:justify-start gap-4 text-xs font-mono opacity-60">
            {profile.location && (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" /> {profile.location}
              </span>
            )}
            {profile.blog && (
              <a
                className="inline-flex items-center gap-1.5 hover:opacity-100"
                href={
                  profile.blog.startsWith("http")
                    ? profile.blog
                    : `https://${profile.blog}`
                }
                target="_blank"
                rel="noreferrer"
              >
                <Link2 className="h-3.5 w-3.5" /> {profile.blog.replace(/^https?:\/\//, "")}
              </a>
            )}
            <a
              className="inline-flex items-center gap-1.5 hover:opacity-100"
              href={profile.html_url}
              target="_blank"
              rel="noreferrer"
            >
              <Github className="h-3.5 w-3.5" /> github
            </a>
          </div>
          <div className="mt-5 flex flex-col sm:flex-row items-center sm:items-start gap-3">
            <motion.button
              onClick={handleDownload}
              disabled={downloading}
              whileHover={{ y: -2, scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              transition={{ type: "spring", stiffness: 380, damping: 22 }}
              className="group glass relative overflow-hidden rounded-xl px-5 py-2.5 inline-flex items-center gap-2 font-mono text-xs sm:text-sm transition-shadow disabled:cursor-not-allowed disabled:opacity-70"
              style={{
                color: "var(--accent-glow)",
                boxShadow:
                  "0 0 0 1px color-mix(in oklab, var(--accent-glow) 22%, transparent), 0 8px 28px -12px color-mix(in oklab, var(--accent-glow) 55%, transparent)",
              }}
            >
              {/* animated sheen */}
              <span
                aria-hidden
                className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 -skew-x-12 bg-gradient-to-r from-transparent via-white/15 to-transparent opacity-0 group-hover:opacity-100 group-hover:translate-x-[260%] transition-all duration-700 ease-out"
              />
              {/* progress fill */}
              <span
                aria-hidden
                className="absolute inset-y-0 left-0 transition-[width] duration-200 ease-out"
                style={{
                  width: `${progress}%`,
                  background:
                    "linear-gradient(90deg, color-mix(in oklab, var(--accent-glow) 28%, transparent), color-mix(in oklab, var(--accent-glow-2, var(--accent-glow)) 22%, transparent))",
                }}
              />
              <span className="relative z-10 inline-flex items-center gap-2">
                <AnimatePresence mode="wait" initial={false}>
                  {downloading ? (
                    <motion.span
                      key="loading"
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.18 }}
                      className="inline-flex items-center gap-2"
                    >
                      <Loader2 className="h-4 w-4 animate-spin" />
                      generating… {Math.round(progress)}%
                    </motion.span>
                  ) : (
                    <motion.span
                      key="idle"
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={{ duration: 0.18 }}
                      className="inline-flex items-center gap-2"
                    >
                      <Download className="h-4 w-4 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:scale-110" />
                      Download PDF Resume
                    </motion.span>
                  )}
                </AnimatePresence>
              </span>
            </motion.button>
            {downloadError && (
              <span className="font-mono text-xs text-red-400/80">
                &gt; error: {downloadError}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Tech */}
      {techSet.length > 0 && (
        <section className="mt-8">
          <h3 className="font-mono text-xs uppercase tracking-widest opacity-60 mb-4 px-1">
            // tech.stack
          </h3>
          <div className="glass rounded-2xl p-5 flex flex-wrap items-center justify-center gap-3 sm:gap-4">
            {techSet.map((t, i) => (
              <motion.span
                key={t}
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.03 * i }}
                className="font-mono text-xs sm:text-sm px-3 py-1.5 rounded-lg glass"
                style={{ color: "var(--accent-glow)" }}
              >
                {t}
              </motion.span>
            ))}
          </div>
        </section>
      )}

      {/* Projects */}
      <section className="mt-10">
        <h3 className="font-mono text-xs uppercase tracking-widest opacity-60 mb-4 px-1">
          // featured.projects
        </h3>
        {projects.length === 0 ? (
          <div className="glass rounded-2xl p-8 text-center font-mono text-sm opacity-60">
            // no public repositories found
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((p, i) => (
              <ProjectCard key={p.title} project={p} index={i} />
            ))}
          </div>
        )}
      </section>

      <p className="text-center text-xs font-mono opacity-40 mt-12">
        generated with ♥ — live data from github.com
      </p>
    </motion.div>
  );
}