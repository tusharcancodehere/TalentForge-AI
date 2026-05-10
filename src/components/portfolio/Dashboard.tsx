import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Github, MapPin, Download, Loader2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { toast } from "sonner";
import { ProjectCard, type Project } from "./ProjectCard";
import {
  fetchPortfolioData,
  type PortfolioProject,
  type PortfolioResponse,
  type PortfolioUser,
} from "@/lib/github";

export function Dashboard({
  username,
  user,
  projects,
  techStack,
  marketInsights,
  initialPagination,
  onBack,
}: {
  username: string;
  user: PortfolioUser;
  projects: PortfolioProject[];
  techStack: string[];
  marketInsights: PortfolioResponse["market_insights"];
  initialPagination: PortfolioResponse["pagination"];
  onBack: () => void;
}) {
  const [downloading, setDownloading] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [page, setPage] = useState(initialPagination.page);
  const [projectItems, setProjectItems] = useState(projects);
  const [pagination, setPagination] = useState(initialPagination);
  const [visitorStats, setVisitorStats] = useState({ active: 0, total: 0 });
  const progressTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch("/api/stats");
        if (res.ok) {
          const data = await res.json();
          setVisitorStats(data);
        }
      } catch (e) {
        // silent fail for stats
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    return () => {
      if (progressTimer.current) clearInterval(progressTimer.current);
    };
  }, []);

  useEffect(() => {
    setProjectItems(projects);
  }, [projects]);

  const loadProjectsPage = async (nextPage: number): Promise<void> => {
    setLoadingProjects(true);
    setPortfolioError(null);
    try {
      const response = await fetchPortfolioData(
        username,
        nextPage,
        initialPagination.page_size,
      );
      setProjectItems(response.projects);
      setPagination(response.pagination);
      setPage(response.pagination.page);
    } catch (err) {
      setPortfolioError(err instanceof Error ? err.message : "Unable to load repositories.");
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    setProgress(4);
    // simulated progress stream — eases toward 90% while we wait
    if (progressTimer.current) clearInterval(progressTimer.current);
    progressTimer.current = setInterval(() => {
      setProgress((p) => (p < 90 ? p + Math.max(1, (92 - p) * 0.08) : p));
    }, 180);
    const toastId = toast.loading("Performing Deep AI Analysis...", {
      description: `analyzing @${username}'s repositories and generating premium resume`,
    });
    try {
      const res = await fetch(`/api/cv/${username}`);
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

  const uiProjects: Project[] = projectItems.map((r) => ({
    title: r.title,
    description: r.ai_description || "No project summary available.",
    tags: r.language ? [r.language] : [],
    stars: r.stars,
    url: r.url,
  }));

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
          src={user.avatar_url}
          alt={`${username} avatar`}
          className="h-24 w-24 rounded-full shrink-0 object-cover"
          style={{
            boxShadow:
              "0 0 0 2px color-mix(in oklab, var(--accent-glow) 50%, transparent)",
          }}
        />
        <div className="flex-1 text-center sm:text-left">
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              {user.name ?? username}
            </h2>
            <span className="font-mono text-xs opacity-50">@{username}</span>
          </div>
          {user.bio && (
            <p className="mt-2 opacity-70 max-w-xl text-sm sm:text-base">
              {user.bio}
            </p>
          )}
          <div className="mt-3 flex flex-wrap items-center justify-center sm:justify-start gap-4 text-xs font-mono opacity-60">
            {user.location && (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" /> {user.location}
              </span>
            )}
            <a
              className="inline-flex items-center gap-1.5 hover:opacity-100"
              href={user.github_url}
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
              className="group brand-button relative overflow-hidden rounded-xl px-5 py-2.5 inline-flex items-center gap-2 font-mono text-xs sm:text-sm transition-shadow disabled:cursor-not-allowed disabled:opacity-70"
              style={{
                color: "oklch(0.13 0.025 270)",
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
                      Generating CV... {Math.round(progress)}%
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
                      Export Premium Resume
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

      {/* Market fit insights */}
      <section className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="glass rounded-2xl p-5 lg:col-span-2">
          <h3 className="font-mono text-xs uppercase tracking-widest opacity-60 mb-2">
            // market.readiness
          </h3>
          <p className="text-sm opacity-80">{marketInsights.summary}</p>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="glass rounded-xl p-3">
              <p className="font-mono text-xs opacity-60">Selection Probability</p>
              <p className="text-2xl font-bold">{marketInsights.selection_probability}%</p>
            </div>
            <div className="glass rounded-xl p-3">
              <p className="font-mono text-xs opacity-60">Estimated Compensation</p>
              <p className="text-sm font-semibold">
                {marketInsights.avg_package.currency} {marketInsights.avg_package.min} -{" "}
                {marketInsights.avg_package.max} ({marketInsights.avg_package.period})
              </p>
              <p className="text-xs opacity-60 mt-1">{marketInsights.avg_package.note}</p>
            </div>
          </div>
        </div>
        <div className="glass rounded-2xl p-5">
          <h3 className="font-mono text-xs uppercase tracking-widest opacity-60 mb-3">
            // skill.ratings
          </h3>
          <div className="space-y-2">
            {marketInsights.market_skill_ratings.slice(0, 6).map((item) => (
              <div key={item.skill}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span>{item.skill}</span>
                  <span className="font-mono opacity-70">{item.score}/10</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(10, item.score * 10))}%`,
                      background:
                        "linear-gradient(90deg, var(--accent-glow), var(--accent-glow-2))",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Career Growth Roadmap */}
      <motion.section
        className="mt-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3, ease: "easeOut" }}
      >
        <div
          className="glass rounded-2xl p-6 sm:p-8 border border-white/[0.06] relative overflow-hidden"
          style={{
            background:
              "linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.005) 50%, rgba(var(--accent-glow-rgb, 130 90 255) / 0.04) 100%)",
          }}
        >
          {/* Subtle background glow */}
          <div
            aria-hidden
            className="pointer-events-none absolute -top-24 -right-24 h-56 w-56 rounded-full opacity-[0.07] blur-3xl"
            style={{ background: "var(--accent-glow)" }}
          />

          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-5 mb-7">
            <div className="flex-1">
              <h3 className="font-mono text-[11px] uppercase tracking-[0.2em] opacity-50 mb-3">
                // CAREER.GROWTH
              </h3>
              <p className="text-base sm:text-lg font-semibold tracking-tight text-white/90 leading-relaxed max-w-2xl">
                {marketInsights.career_growth?.roadmap_summary || "Analyzing your growth trajectory..."}
              </p>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              <div className="text-right">
                <p className="text-[9px] font-mono opacity-35 uppercase tracking-wider mb-1">Potential Lift</p>
                <p className="text-2xl font-bold text-green-400 tabular-nums">
                  +{(marketInsights.career_growth?.target_score || 0) - (marketInsights.career_growth?.current_score || 0)}%
                </p>
              </div>
              <div className="h-12 w-px bg-white/[0.08]" />
              <div className="text-right">
                <p className="text-[9px] font-mono opacity-35 uppercase tracking-wider mb-1">Target</p>
                <p className="text-2xl font-bold opacity-80 tabular-nums">{marketInsights.career_growth?.target_score}%</p>
              </div>
            </div>
          </div>

          {/* Animated Progress Bar */}
          <div className="mb-7">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-[10px] opacity-40 uppercase tracking-wider">
                Selection Probability
              </span>
              <span className="font-mono text-xs font-bold opacity-70 tabular-nums">
                {marketInsights.career_growth?.current_score ?? marketInsights.selection_probability}%
              </span>
            </div>
            <div className="h-3 rounded-full bg-white/[0.06] overflow-hidden relative">
              {/* Glow underlay */}
              <motion.div
                className="absolute inset-y-0 left-0 rounded-full blur-sm"
                initial={{ width: 0 }}
                animate={{ width: `${marketInsights.career_growth?.current_score ?? marketInsights.selection_probability}%` }}
                transition={{ duration: 1.8, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
                style={{
                  background: "linear-gradient(90deg, var(--accent-glow), var(--accent-glow-2, var(--accent-glow)))",
                  opacity: 0.5,
                }}
              />
              {/* Main bar */}
              <motion.div
                className="absolute inset-y-0 left-0 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${marketInsights.career_growth?.current_score ?? marketInsights.selection_probability}%` }}
                transition={{ duration: 1.6, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
                style={{
                  background: "linear-gradient(90deg, var(--accent-glow), var(--accent-glow-2, var(--accent-glow)))",
                }}
              />
              {/* Target indicator line */}
              {marketInsights.career_growth?.target_score && (
                <motion.div
                  className="absolute top-0 bottom-0 w-px"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 2.2, duration: 0.4 }}
                  style={{
                    left: `${marketInsights.career_growth.target_score}%`,
                    background: "rgba(255,255,255,0.5)",
                    boxShadow: "0 0 6px rgba(255,255,255,0.3)",
                  }}
                />
              )}
            </div>
            {/* Bar labels */}
            <div className="flex items-center justify-between mt-1.5">
              <span className="font-mono text-[9px] opacity-25">0%</span>
              {marketInsights.career_growth?.target_score && (
                <span
                  className="font-mono text-[9px] text-green-400/60"
                  style={{ marginLeft: `${marketInsights.career_growth.target_score - 8}%` }}
                >
                  ↑ target
                </span>
              )}
              <span className="font-mono text-[9px] opacity-25">100%</span>
            </div>
          </div>

          {/* Recommended Skill Badges — Staggered Fade-in */}
          <div className="mb-5">
            <p className="font-mono text-[10px] uppercase tracking-wider opacity-40 mb-3">
              Recommended Skills
            </p>
            <div className="flex flex-wrap gap-3">
              {marketInsights.career_growth?.recommended_skills.map((skill, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, scale: 0.8, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ duration: 0.45, delay: 0.8 + idx * 0.2, ease: "easeOut" }}
                  whileHover={{ scale: 1.05, y: -2 }}
                  className="group relative cursor-default"
                >
                  <div
                    className="glass rounded-xl px-5 py-3 border border-white/[0.06] transition-all duration-300 group-hover:border-white/[0.12]"
                    style={{
                      background:
                        "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(var(--accent-glow-rgb, 130 90 255) / 0.06) 100%)",
                    }}
                  >
                    {/* Glow dot */}
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <div
                        className="h-2 w-2 rounded-full"
                        style={{
                          background: "var(--accent-glow)",
                          boxShadow: "0 0 10px var(--accent-glow), 0 0 20px color-mix(in oklab, var(--accent-glow) 40%, transparent)",
                        }}
                      />
                      <h4 className="font-mono text-sm font-bold text-white/85 group-hover:text-white transition-colors">
                        {skill.skill}
                      </h4>
                    </div>
                    <p className="text-[11px] opacity-50 leading-relaxed pl-[18px] max-w-[220px]">
                      {skill.why}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Call to Action */}
          {marketInsights.career_growth?.recommended_skills?.[0] && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.6, duration: 0.5 }}
              className="glass rounded-lg px-4 py-3 border border-green-400/10"
              style={{ background: "rgba(74, 222, 128, 0.04)" }}
            >
              <p className="text-xs text-green-400/80 font-mono">
                <span className="opacity-60">→</span>{" "}
                Mastering{" "}
                <span className="font-bold text-green-400">
                  {marketInsights.career_growth.recommended_skills[0].skill}
                </span>{" "}
                could boost your market readiness by{" "}
                <span className="font-bold text-green-400">
                  +{(marketInsights.career_growth.target_score - marketInsights.career_growth.current_score)}%
                </span>
              </p>
            </motion.div>
          )}
        </div>
      </motion.section>
      {techStack.length > 0 && (
        <section className="mt-8">
          <h3 className="font-mono text-xs uppercase tracking-widest opacity-60 mb-4 px-1">
            // tech.stack
          </h3>
          <div className="glass rounded-2xl p-5 flex flex-wrap items-center justify-center gap-3 sm:gap-4">
            {techStack.map((t, i) => (
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
        {pagination.total_projects === 0 ? (
          <div className="glass rounded-2xl p-8 text-center font-mono text-sm opacity-60">
            // no public repositories found
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {uiProjects.map((p, i) => (
                <ProjectCard key={p.title} project={p} index={i} />
              ))}
            </div>
            <div className="glass rounded-xl p-3 flex items-center justify-between">
              <button
                onClick={() => loadProjectsPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="font-mono text-xs px-3 py-1.5 rounded-md glass disabled:opacity-40"
              >
                Previous
              </button>
              <span className="font-mono text-xs opacity-70">
                {loadingProjects ? "Loading..." : `Page ${page} / ${pagination.total_pages}`}
              </span>
              <button
                onClick={() => loadProjectsPage(Math.min(pagination.total_pages, page + 1))}
                disabled={page >= pagination.total_pages}
                className="font-mono text-xs px-3 py-1.5 rounded-md glass disabled:opacity-40"
              >
                Next
              </button>
            </div>
            <p className="text-center font-mono text-xs opacity-60">
              Showing {(page - 1) * pagination.page_size + 1}-
              {Math.min(page * pagination.page_size, pagination.total_projects)} of{" "}
              {pagination.total_projects} repositories
            </p>
            {portfolioError && (
              <p className="text-center font-mono text-xs text-red-400/80">{portfolioError}</p>
            )}
          </div>
        )}
      </section>

      <div className="mt-12 flex flex-col items-center gap-2">
        <p className="text-center text-xs font-mono opacity-40">
          Powered by TalentForge AI | Built from live GitHub intelligence
        </p>
        <div className="flex items-center gap-4 font-mono text-[10px] uppercase tracking-wider opacity-30">
          <span className="flex items-center gap-1.5">
            <span className="h-1 w-1 rounded-full bg-green-500 animate-pulse" />
            {visitorStats.active} active explorers
          </span>
          <span className="opacity-50">|</span>
          <span>{visitorStats.total} unique architects</span>
        </div>
      </div>
    </motion.div>
  );
}