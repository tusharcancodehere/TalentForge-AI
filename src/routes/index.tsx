import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Hero } from "@/components/portfolio/Hero";
import { Dashboard } from "@/components/portfolio/Dashboard";
import { ThemeToggle } from "@/components/theme-toggle";
import { Code2 } from "lucide-react";
import {
  fetchGitHubUser,
  type GitHubProfile,
  type GitHubRepo,
} from "@/lib/github";

export const Route = createFileRoute("/")({
  component: Index,
  head: () => ({
    meta: [
      { title: "Portfoli.io — Deploy your dev portfolio in 60 seconds" },
      {
        name: "description",
        content:
          "Zero-effort developer portfolio generator. Drop your GitHub username and get a beautiful glassmorphic portfolio instantly.",
      },
    ],
  }),
});

function Index() {
  const [data, setData] = useState<
    { profile: GitHubProfile; repos: GitHubRepo[] } | null
  >(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (username: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchGitHubUser(username);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ambient-bg relative min-h-screen overflow-x-hidden">
      <header className="flex items-center justify-between px-6 sm:px-10 py-6 max-w-6xl mx-auto">
        <div className="inline-flex items-center gap-2 font-mono text-sm font-semibold">
          <span
            className="h-7 w-7 rounded-lg flex items-center justify-center"
            style={{
              background:
                "linear-gradient(135deg, var(--accent-glow), var(--accent-glow-2))",
            }}
          >
            <Code2 className="h-4 w-4" style={{ color: "oklch(0.13 0.025 270)" }} />
          </span>
          portfoli<span style={{ color: "var(--accent-glow)" }}>.io</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="px-5 sm:px-10 pb-24 pt-8 sm:pt-16 flex items-start justify-center">
        <AnimatePresence mode="wait">
          {data ? (
            <Dashboard
              key="dashboard"
              profile={data.profile}
              repos={data.repos}
              onBack={() => {
                setData(null);
                setError(null);
              }}
            />
          ) : (
            <Hero
              key="hero"
              onGenerate={handleGenerate}
              loading={loading}
              error={error}
            />
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
