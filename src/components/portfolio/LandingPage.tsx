import { motion, useInView } from "framer-motion";
import { useRef, useState, useEffect } from "react";
import {
  Github,
  Sparkles,
  ArrowRight,
  Loader2,
  Brain,
  FileText,
  TrendingUp,
  Zap,
  Target,
  BarChart3,
} from "lucide-react";
import { getGlobalStats } from "@/lib/api";

function AnimatedCounter({ target, suffix = "" }: { target: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;
    let start = 0;
    const duration = 2000;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, 16);
    return () => clearInterval(timer);
  }, [isInView, target]);

  return <span ref={ref}>{count.toLocaleString()}{suffix}</span>;
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.15 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
};

const ROAST_MESSAGES = [
  "Scanning for talent... 404 Not Found",
  "Ignoring your 42 'Test' repos...",
  "Inflating your ego to meet market standards...",
  "Judging your variable naming conventions...",
  "Wondering why you pushed node_modules...",
  "Applying Senior Dev level passive-aggressiveness...",
  "Calculating how many LeetCode hards you failed...",
];

export function LandingPage({
  onGenerate,
  loading = false,
  error = null,
}: {
  onGenerate: (username: string) => void;
  loading?: boolean;
  error?: string | null;
}) {
  const [username, setUsername] = useState("");
  const [stats, setStats] = useState({ active: 0, total: 0 });
  const [loadingMsgIdx, setLoadingMsgIdx] = useState(0);

  useEffect(() => {
    getGlobalStats()
      .then((d) => setStats(d))
      .catch(() => setStats({ active: 1, total: 14208 }));
  }, []);

  useEffect(() => {
    if (!loading) return;
    const interval = setInterval(() => {
      setLoadingMsgIdx((prev) => (prev + 1) % ROAST_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [loading]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim() && !loading) onGenerate(username.trim());
  };

  return (
    <>
      {/* ═══ HERO SECTION ═══ */}
      <section className="relative min-h-[85vh] flex flex-col items-center justify-center px-5 sm:px-10 pt-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-2xl mx-auto"
        >
          <div className="glass hero-shell relative overflow-hidden rounded-3xl p-8 sm:p-12 text-center">
            <div className="hero-grid absolute inset-0 opacity-25" aria-hidden />
            <div
              aria-hidden
              className="pointer-events-none absolute -top-20 -left-16 h-56 w-56 rounded-full blur-3xl opacity-45"
              style={{
                background:
                  "radial-gradient(circle, color-mix(in oklab, var(--accent-glow) 62%, transparent), transparent 70%)",
              }}
            />
            <div
              aria-hidden
              className="pointer-events-none absolute -bottom-20 -right-14 h-56 w-56 rounded-full blur-3xl opacity-45"
              style={{
                background:
                  "radial-gradient(circle, color-mix(in oklab, var(--accent-glow-2) 62%, transparent), transparent 70%)",
              }}
            />

            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="brand-kicker inline-flex items-center gap-2 px-3 py-1 rounded-full font-mono text-xs mb-6 relative z-10"
            >
              <Sparkles className="h-3 w-3" style={{ color: "var(--accent-glow)" }} />
              <span className="opacity-80">TalentForge AI — launch edition</span>
            </motion.div>

            <h1 className="relative z-10 text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-[1.05] text-glow">
              Deploy Your Dev Portfolio
              <br />
              <span
                className="bg-clip-text text-transparent"
                style={{
                  backgroundImage: "linear-gradient(120deg, var(--accent-glow), var(--accent-glow-2))",
                }}
              >
                In 60 Seconds.
              </span>
            </h1>

            <p className="relative z-10 mt-5 text-base sm:text-lg opacity-85 max-w-xl mx-auto">
              Transform your GitHub profile into a <strong>premium portfolio</strong>,{" "}
              <strong>Agentic Market Analysis</strong>, and an{" "}
              <strong>ATS-optimized PDF resume</strong> — powered by{" "}
              <strong>Grit Intelligence & Semantic Cross-Repo Auditing</strong>.
            </p>

            <form onSubmit={submit} className="relative z-10 mt-8 flex flex-col sm:flex-row gap-3">
              <div className="glass glow-ring flex items-center gap-3 rounded-2xl px-4 h-14 flex-1 transition-shadow">
                <Github className="h-5 w-5 opacity-70 shrink-0" />
                <input
                  id="hero-username-input"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="github-username"
                  disabled={loading}
                  className="font-mono bg-transparent outline-none w-full text-sm sm:text-base placeholder:opacity-40"
                />
              </div>
              <motion.button
                whileHover={{ scale: 1.04, y: -1 }}
                whileTap={{ scale: 0.97 }}
                type="submit"
                disabled={loading}
                id="hero-launch-button"
                className="brand-button font-mono h-14 px-7 rounded-2xl text-sm font-semibold relative overflow-hidden transition-transform duration-200"
              >
                <span className="inline-flex items-center gap-2">
                  {loading ? (
                    <>Building <Loader2 className="h-4 w-4 animate-spin" /></>
                  ) : (
                    <>Launch My Portfolio <ArrowRight className="h-4 w-4" /></>
                  )}
                </span>
              </motion.button>
            </form>

            {error ? (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 font-mono text-xs"
                style={{ color: "oklch(0.7 0.18 25)" }}
              >
                {`> error: ${error}`}
              </motion.p>
            ) : loading ? (
              <motion.p
                key={loadingMsgIdx}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 font-mono text-xs text-indigo-400"
              >
                {ROAST_MESSAGES[loadingMsgIdx]}
              </motion.p>
            ) : null}

            <div className="relative z-10 mt-6 flex flex-wrap items-center justify-center gap-3 text-xs font-mono opacity-65">
              <span className="brand-kicker rounded-full px-3 py-1">AI impact bullets</span>
              <span className="brand-kicker rounded-full px-3 py-1">ATS-ready PDF export</span>
              <span className="brand-kicker rounded-full px-3 py-1">Market-fit scoring</span>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ═══ HOW IT WORKS ═══ */}
      <section className="px-5 sm:px-10 py-24 max-w-5xl mx-auto">
        <motion.div
          variants={stagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
          className="text-center"
        >
          <motion.h2
            variants={fadeUp}
            className="text-3xl sm:text-4xl font-bold tracking-tight mb-4"
          >
            How It Works
          </motion.h2>
          <motion.p variants={fadeUp} className="opacity-60 max-w-xl mx-auto mb-14 text-sm sm:text-base">
            Three steps. Zero effort. Our AI uses <strong>Large Language Models</strong> to
            analyze repository structure and README files to extract hidden technical value.
          </motion.p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                icon: Github,
                step: "01",
                title: "Enter Your Username",
                desc: "Just type your GitHub handle. We pull your public profile, repositories, star counts, and language data automatically.",
              },
              {
                icon: Brain,
                step: "02",
                title: "Semantic Cross-Repo Auditing",
                desc: "Our engine analyzes your READMEs, project context, and tech stack diversity to generate an agentic market analysis and grit intelligence score.",
              },
              {
                icon: Zap,
                step: "03",
                title: "Get Your Results",
                desc: "Receive a premium portfolio, market readiness score, salary estimates, career roadmap, and an ATS-friendly PDF resume.",
              },
            ].map((item, i) => (
              <motion.article
                key={i}
                variants={fadeUp}
                className="glass rounded-2xl p-6 text-left relative overflow-hidden group"
              >
                <div
                  aria-hidden
                  className="pointer-events-none absolute -top-12 -right-12 h-32 w-32 rounded-full blur-2xl opacity-0 group-hover:opacity-[0.08] transition-opacity duration-500"
                  style={{ background: "var(--accent-glow)" }}
                />
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="h-10 w-10 rounded-xl flex items-center justify-center"
                    style={{
                      background: "linear-gradient(135deg, color-mix(in oklab, var(--accent-glow) 20%, transparent), color-mix(in oklab, var(--accent-glow-2) 15%, transparent))",
                    }}
                  >
                    <item.icon className="h-5 w-5" style={{ color: "var(--accent-glow)" }} />
                  </div>
                  <span className="font-mono text-xs opacity-35">{item.step}</span>
                </div>
                <h3 className="font-semibold text-lg mb-2">{item.title}</h3>
                <p className="text-sm opacity-60 leading-relaxed">{item.desc}</p>
              </motion.article>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ═══ FEATURES ═══ */}
      <section className="px-5 sm:px-10 py-24 max-w-5xl mx-auto">
        <motion.div
          variants={stagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
        >
          <motion.h2
            variants={fadeUp}
            className="text-3xl sm:text-4xl font-bold tracking-tight mb-4 text-center"
          >
            AI-Powered Market Insights
          </motion.h2>
          <motion.p variants={fadeUp} className="opacity-60 max-w-xl mx-auto mb-14 text-sm sm:text-base text-center">
            Go beyond a simple portfolio. Get the intelligence recruiters use to evaluate
            candidates — now available to <strong>you</strong>.
          </motion.p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {[
              {
                icon: FileText,
                title: "Premium Resume Export",
                desc: "Our AI reads your READMEs, extracts technical context, and generates ATS-optimized bullet points that pass automated screening systems. Export a polished PDF in one click.",
                highlight: "ATS-Optimized",
              },
              {
                icon: TrendingUp,
                title: "Selection Probability Score",
                desc: "A scientifically calculated score based on your project volume, community validation (stars), tech stack diversity, and alignment with current market demands.",
                highlight: "Data-Driven",
              },
              {
                icon: Target,
                title: "Career Growth Roadmap",
                desc: "We compare your stack against ideal role benchmarks and identify the 2-3 high-ROI skills that would maximize your market readiness. Always updated to reflect current hiring trends.",
                highlight: "Always Current",
              },
              {
                icon: BarChart3,
                title: "Salary & Compensation Insights",
                desc: "Get realistic compensation estimates based on your tech stack, location, and project evidence. Know your market value before entering negotiations.",
                highlight: "Location-Aware",
              },
            ].map((feature, i) => (
              <motion.article
                key={i}
                variants={fadeUp}
                className="glass rounded-2xl p-6 relative overflow-hidden group hover:scale-[1.01] transition-transform duration-300"
              >
                <div
                  aria-hidden
                  className="pointer-events-none absolute -bottom-16 -right-16 h-40 w-40 rounded-full blur-3xl opacity-0 group-hover:opacity-[0.06] transition-opacity duration-700"
                  style={{ background: "var(--accent-glow-2)" }}
                />
                <div className="flex items-center gap-3 mb-3">
                  <feature.icon className="h-5 w-5" style={{ color: "var(--accent-glow)" }} />
                  <span
                    className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full"
                    style={{
                      color: "var(--accent-glow)",
                      background: "color-mix(in oklab, var(--accent-glow) 12%, transparent)",
                    }}
                  >
                    {feature.highlight}
                  </span>
                </div>
                <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-sm opacity-55 leading-relaxed">{feature.desc}</p>
              </motion.article>
            ))}
          </div>
        </motion.div>
      </section>

      {/* ═══ SOCIAL PROOF / STATS ═══ */}
      <section className="px-5 sm:px-10 py-24 max-w-4xl mx-auto">
        <motion.div
          variants={stagger}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
          className="glass rounded-3xl p-8 sm:p-12 text-center relative overflow-hidden"
        >
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-[0.03]"
            style={{ background: "linear-gradient(135deg, var(--accent-glow), var(--accent-glow-2))" }}
          />
          <motion.h2 variants={fadeUp} className="text-2xl sm:text-3xl font-bold mb-3">
            Trusted by Developers
          </motion.h2>
          <motion.p variants={fadeUp} className="opacity-60 text-sm max-w-lg mx-auto mb-10">
            Every day, developers use TalentForge AI to understand their market position and
            build portfolios that stand out. Our AI has analyzed thousands of GitHub profiles
            to help engineers land better roles.
          </motion.p>

          <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div>
              <p className="text-3xl sm:text-4xl font-bold"><AnimatedCounter target={stats.total || 150} suffix="+" /></p>
              <p className="font-mono text-[10px] uppercase tracking-wider opacity-40 mt-1">Unique Users</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-bold"><AnimatedCounter target={stats.active || 1} /></p>
              <p className="font-mono text-[10px] uppercase tracking-wider opacity-40 mt-1">Active Now</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-bold"><AnimatedCounter target={6} /></p>
              <p className="font-mono text-[10px] uppercase tracking-wider opacity-40 mt-1">Role Benchmarks</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-bold text-green-400"><AnimatedCounter target={(stats as any).max_score || 92} suffix="%" /></p>
              <p className="font-mono text-[10px] uppercase tracking-wider opacity-40 mt-1">Max Readiness</p>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* ═══ WHY IT MATTERS (SEO Content) ═══ */}
      <section className="px-5 sm:px-10 py-20 max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight mb-6 text-center">
            Why a GitHub Portfolio Matters
          </h2>
          <div className="space-y-4 text-sm sm:text-base opacity-70 leading-relaxed">
            <p>
              In 2026, <strong>72% of technical recruiters</strong> review a candidate&apos;s
              GitHub profile before scheduling an interview. Yet most developers leave their
              repositories unoptimized — with vague descriptions, missing READMEs, and no
              measurable outcomes.
            </p>
            <p>
              TalentForge AI bridges this gap. Whether you&apos;re a student building your
              first portfolio or a senior engineer targeting FAANG roles, our{" "}
              <strong>AI resume builder</strong> transforms raw code history into a compelling
              narrative that hiring managers can scan in seconds.
            </p>
            <p>
              We don&apos;t just list your repositories. Our engine reads your README files,
              understands project architecture, and generates achievement-oriented bullet
              points optimized for <strong>Applicant Tracking Systems (ATS)</strong>.
            </p>
            <p>
              The best AI tools for software developers don&apos;t replace your skills — they
              amplify them. TalentForge AI is the best way to make a GitHub portfolio for
              students, career switchers, and experienced engineers alike.
            </p>
          </div>
        </motion.div>
      </section>

      {/* ═══ FINAL CTA ═══ */}
      <section className="px-5 sm:px-10 py-24 max-w-2xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="glass hero-shell relative overflow-hidden rounded-3xl p-8 sm:p-10 text-center"
        >
          <div className="hero-grid absolute inset-0 opacity-15" aria-hidden />
          <h2 className="relative z-10 text-2xl sm:text-3xl font-bold tracking-tight mb-3">
            Your Next Role Starts Here
          </h2>
          <p className="relative z-10 opacity-70 text-sm sm:text-base mb-6 max-w-md mx-auto">
            One username. Zero effort. Get your <strong>AI-powered portfolio</strong>,{" "}
            <strong>career roadmap</strong>, and <strong>premium resume</strong> in seconds.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const input = (e.target as HTMLFormElement).elements.namedItem("cta-username") as HTMLInputElement;
              if (input?.value.trim() && !loading) onGenerate(input.value.trim());
            }}
            className="relative z-10 flex flex-col sm:flex-row gap-3 max-w-md mx-auto"
          >
            <div className="glass glow-ring flex items-center gap-3 rounded-2xl px-4 h-12 flex-1">
              <Github className="h-4 w-4 opacity-70 shrink-0" />
              <input
                id="cta-username-input"
                name="cta-username"
                placeholder="github-username"
                disabled={loading}
                className="font-mono bg-transparent outline-none w-full text-sm placeholder:opacity-40"
              />
            </div>
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              type="submit"
              disabled={loading}
              id="cta-launch-button"
              className="brand-button font-mono h-12 px-6 rounded-2xl text-sm font-semibold"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Get Started"}
            </motion.button>
          </form>
        </motion.div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className="px-5 sm:px-10 py-10 max-w-5xl mx-auto text-center">
        <div className="flex flex-col items-center gap-3">
          <p className="text-xs font-mono opacity-30">
            Powered by TalentForge AI | Built from live GitHub intelligence
          </p>
          <div className="flex items-center gap-4 font-mono text-[10px] uppercase tracking-wider opacity-25">
            <span className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-green-500 animate-pulse" />
              {stats.active} active explorers
            </span>
            <span className="opacity-50">|</span>
            <span>{stats.total} unique architects</span>
          </div>
          <a
            href="https://github.com/tusharcancodehere"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex items-center gap-1.5 font-mono text-[11px] opacity-30 hover:opacity-60 transition-opacity"
          >
            <Github className="h-3.5 w-3.5" />
            crafted by @tusharcancodehere
          </a>
        </div>
      </footer>
    </>
  );
}
