import { motion } from "framer-motion";
import { ArrowLeft, Github, MapPin, Link2, Download, Loader2 } from "lucide-react";
import { useState } from "react";
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

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
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
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloading(false);
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
          <div className="mt-5 flex flex-col sm:flex-row items-center sm:items-start gap-2">
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="glass rounded-xl px-4 py-2.5 inline-flex items-center gap-2 font-mono text-xs sm:text-sm hover:opacity-100 opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: "var(--accent-glow)" }}
            >
              {downloading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  generating...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Download PDF Resume
                </>
              )}
            </button>
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