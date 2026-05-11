import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { LandingPage } from "@/components/portfolio/LandingPage";
import { CareerArchitectPanel } from "@/components/portfolio/CareerArchitectPanel";
import { ThemeToggle } from "@/components/theme-toggle";
import { BrandLogo } from "@/components/BrandLogo";
import { analyzeProfile } from "@/lib/api";
import { type CareerArchitectResponse } from "@/lib/github";
import { toast } from "sonner";

export const Route = createFileRoute("/")(
  {
  component: Index,
  head: () => ({
    meta: [
      { title: "TalentForge AI | Zero-Effort GitHub Portfolio & CV Generator" },
      {
        name: "description",
        content:
          "Instantly transform your GitHub profile into a premium, AI-powered portfolio and ATS-friendly PDF resume. Get market readiness scores and salary estimates.",
      },
      {
        name: "keywords",
        content:
          "GitHub Portfolio Generator, AI Resume Builder, Developer CV Tool, TalentForge AI, Glassport Gen, best AI tools for software developers, how to make a GitHub portfolio for students",
      },
      {
        property: "og:title",
        content: "Build an Elite Portfolio in 60 Seconds",
      },
      {
        property: "og:description",
        content:
          "See your market readiness score and get an AI-written CV. Powered by Gemini 1.5 Pro.",
      },
    ],
  }),
});

function Index() {
  const [data, setData] = useState<CareerArchitectResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (username: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeProfile(username);
      setData(result);
    } catch (err) {
      if (err instanceof Error && err.message.includes("Render server timeout")) {
        toast.error("Render server timeout. Retrying with deterministic fallback...");
        // the backend handles the fallback, but if we get here the fallback also failed or the gateway failed.
      }
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ambient-bg relative min-h-screen overflow-x-hidden">
      <nav className="flex items-center justify-between px-6 sm:px-10 py-6 max-w-6xl mx-auto">
        <BrandLogo />
        <ThemeToggle />
      </nav>

      <main>
        <AnimatePresence mode="wait">
          {data ? (
            <div key="architect" className="px-5 sm:px-10 pb-24 pt-8 sm:pt-16 flex items-start justify-center">
              <CareerArchitectPanel
                data={data}
                onClose={() => {
                  setData(null);
                  setError(null);
                }}
              />
            </div>
          ) : (
            <LandingPage
              key="landing"
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

function usernameFromGithubUrl(url: string): string {
  const segments = url.split("/").filter(Boolean);
  return segments[segments.length - 1] || "octocat";
}
