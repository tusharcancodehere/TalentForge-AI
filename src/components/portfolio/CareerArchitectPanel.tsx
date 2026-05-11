import { motion, AnimatePresence } from "framer-motion";
import {
  X, Briefcase, DollarSign, MessageSquare, Send, Loader2, Zap,
  Target, ArrowRight, Shield, Layers, Code, Hash, Globe, Download
} from "lucide-react";
import { useState, useRef, useEffect } from "react";
import type { CareerArchitectResponse } from "@/lib/github";
import { API_BASE_URL } from "@/lib/github";
import { toast } from "sonner";

import { chatWithCoach, exportCV } from "@/lib/api";

type ChatMessage = { role: "user" | "coach"; content: string };

/* ── Score & Tier Logic ────────────────────────────────────────── */
function getTier(score: number) {
  if (score >= 85) return "Elite";
  if (score >= 65) return "Market-Ready";
  if (score >= 40) return "Emerging";
  return "Junior";
}

const TIER_STYLES: Record<string, { gradient: string; text: string; glow: string }> = {
  Elite:        { gradient: "from-amber-400 to-orange-500", text: "text-amber-300",  glow: "shadow-amber-500/30" },
  "Market-Ready": { gradient: "from-emerald-400 to-teal-500", text: "text-emerald-300", glow: "shadow-emerald-500/30" },
  Emerging:     { gradient: "from-sky-400 to-indigo-500",  text: "text-sky-300",    glow: "shadow-sky-500/30" },
  Junior:       { gradient: "from-slate-400 to-slate-500", text: "text-slate-300",  glow: "shadow-slate-500/30" },
};

/* ── Score ring (SVG) ──────────────────────────────────────────── */
function ScoreRing({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const tier = getTier(score);

  return (
    <div className="relative flex items-center justify-center">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
        <motion.circle
          cx="70" cy="70" r={radius} fill="none"
          stroke="url(#scoreGrad)" strokeWidth="10" strokeLinecap="round"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.4, ease: "easeOut" }}
          strokeDasharray={circumference}
        />
        <defs>
          <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={tier === "Elite" ? "#f59e0b" : tier === "Market-Ready" ? "#34d399" : tier === "Emerging" ? "#38bdf8" : "#94a3b8"} />
            <stop offset="100%" stopColor={tier === "Elite" ? "#f97316" : tier === "Market-Ready" ? "#14b8a6" : tier === "Emerging" ? "#6366f1" : "#64748b"} />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-black tabular-nums">{score}</span>
        <span className="text-[10px] uppercase tracking-widest opacity-50">/ 100</span>
      </div>
    </div>
  );
}

/* ── Main Panel ─────────────────────────────────────────────────── */
export function CareerArchitectPanel({
  data,
  onClose,
}: {
  data: CareerArchitectResponse | null;
  onClose: () => void;
}) {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showResume, setShowResume] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, isTyping]);

  const handleSendMessage = async () => {
    if (!currentMessage.trim() || !data) return;
    const newMsg: ChatMessage = { role: "user", content: currentMessage };
    setChatMessages((prev) => [...prev, newMsg]);
    setCurrentMessage("");
    setIsTyping(true);
    try {
      const result = await chatWithCoach(newMsg.content, data);
      setChatMessages((prev) => [...prev, { role: "coach", content: result.response }]);
    } catch {
      setChatMessages((prev) => [...prev, { role: "coach", content: "Network issue. Please try again." }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleExport = async () => {
    if (!data) return;
    setIsExporting(true);
    const toastId = toast.loading("Generating Premium CV...");
    try {
      const blob = await exportCV("developer", data.resume_html, data.architect_classification);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "talentforge_resume.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("CV ready", { id: toastId, description: "Resume downloaded successfully" });
    } catch (e) {
      toast.error("Export failed", { id: toastId, description: e instanceof Error ? e.message : "Unknown error" });
    } finally {
      setIsExporting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
  };

  if (!data) return null;

  const score = data.economic_analysis.readiness_score;
  const tier = getTier(score);
  const tierStyle = TIER_STYLES[tier];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-5xl mx-auto rounded-3xl relative"
        style={{
          background: "linear-gradient(145deg, rgba(15,23,42,0.97), rgba(10,15,30,0.99))",
          boxShadow: "0 0 120px rgba(99,102,241,0.08), inset 0 1px 0 rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {/* Back Button */}
        <button onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full hover:bg-white/10 transition-colors z-10 backdrop-blur-sm"
        >
          <X className="h-5 w-5 opacity-60 hover:opacity-100 transition-opacity" />
        </button>

        <div className="p-6 sm:p-10 space-y-8">
            {/* ═══ Header ═══ */}
            <div className="flex items-start gap-4 justify-between flex-wrap">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/10">
                  <Briefcase className="h-7 w-7 text-indigo-400" />
                </div>
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
                    Career Architect <span className="text-indigo-400">Protocol</span>
                  </h2>
                  <p className="opacity-50 text-xs mt-1 font-mono tracking-wider">
                    TALENTFORGE AI · 2026 MARKET ANALYSIS
                  </p>
                </div>
              </div>
              {data.architect_classification && (
                <div className={`px-4 py-1.5 rounded-full border text-xs font-bold tracking-widest uppercase mt-1
                  ${data.architect_classification === "System Architect" 
                    ? "bg-purple-500/10 border-purple-500/30 text-purple-300" 
                    : "bg-indigo-500/10 border-indigo-500/30 text-indigo-300"}`}
                >
                  {data.architect_classification}
                </div>
              )}
            </div>

            {/* ═══ Executive Summary ═══ */}
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
              className="rounded-2xl p-6 border border-white/5"
              style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.06), rgba(139,92,246,0.04))" }}
            >
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-indigo-400 mb-3 flex items-center gap-2">
                <Zap className="h-3.5 w-3.5" /> Executive Summary
              </p>
              <p className="text-sm sm:text-base leading-relaxed opacity-85">{data.executive_summary}</p>
            </motion.div>

            {/* ═══ Economic Engine: Readiness + Compensation ═══ */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Score Ring */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}
                className={`rounded-2xl p-6 border border-white/5 flex flex-col items-center justify-center gap-3 ${tierStyle.glow}`}
                style={{ background: "rgba(255,255,255,0.02)" }}
              >
                <ScoreRing score={score} />
                <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase bg-gradient-to-r ${tierStyle.gradient} text-black`}>
                  {tier}
                </span>
                <span className="text-[10px] font-mono opacity-40 uppercase tracking-wider">Readiness Score</span>
              </motion.div>

              {/* Compensation */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.25 }}
                className="rounded-2xl p-6 border border-white/5 relative overflow-hidden flex flex-col justify-center"
                style={{ background: "rgba(255,255,255,0.02)" }}
              >
                <div className="absolute -top-4 -right-4 opacity-[0.04]">
                  <DollarSign className="h-32 w-32" />
                </div>
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] opacity-40 mb-6 flex items-center gap-2">
                  <Target className="h-3 w-3" /> 2026 Economic Projection
                </p>
                <div className="space-y-4">
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs opacity-40 font-mono">CTC (INR)</span>
                    <span className="text-2xl font-bold text-emerald-400">{data.economic_analysis.compensation.INR}</span>
                  </div>
                  <div className="h-px bg-white/5" />
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs opacity-40 font-mono">CTC (USD)</span>
                    <span className="text-xl font-bold text-sky-400">{data.economic_analysis.compensation.USD}</span>
                  </div>
                </div>
              </motion.div>
            </div>

            {/* ═══ Gap-Closer Blueprint ═══ */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
              <div className="rounded-2xl border border-indigo-500/20 overflow-hidden" style={{ background: "rgba(99,102,241,0.03)" }}>
                <div className="bg-indigo-500/10 p-4 border-b border-indigo-500/20 flex items-center gap-3">
                  <Shield className="h-5 w-5 text-indigo-400" />
                  <h3 className="font-bold text-indigo-100">Gap-Closer Blueprint</h3>
                  <span className="ml-auto px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono tracking-widest uppercase border border-emerald-500/20">
                    {data.blueprint.market_value_boost} Boost
                  </span>
                </div>
                <div className="p-6 space-y-6">
                  <div>
                    <h4 className="text-xl font-bold mb-1 text-white/90">{data.blueprint.project_name}</h4>
                    <p className="text-sm opacity-70 leading-relaxed">{data.blueprint.elevator_pitch}</p>
                  </div>
                  
                  <div className="grid sm:grid-cols-2 gap-6">
                    <div>
                      <p className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 mb-2 flex items-center gap-2">
                        <Layers className="h-3 w-3" /> Tech Stack
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {data.blueprint.the_stack.map((t, i) => (
                          <span key={i} className="px-2.5 py-1 rounded-md text-xs bg-white/5 border border-white/10 text-white/80 font-mono">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 mb-2 flex items-center gap-2">
                        <Code className="h-3 w-3" /> Architecture
                      </p>
                      <p className="text-sm opacity-70 leading-relaxed">{data.blueprint.core_architecture}</p>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-white/5">
                    <p className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 mb-3 flex items-center gap-2">
                      <ArrowRight className="h-3 w-3" /> Implementation Plan
                    </p>
                    <ul className="space-y-2">
                      {data.blueprint.implementation_milestones.map((m, i) => (
                        <li key={i} className="flex gap-3 text-sm opacity-80 items-start">
                          <span className="text-indigo-400 mt-0.5">•</span>
                          {m}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* ═══ SEO & Social Metadata ═══ */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}
              className="grid grid-cols-1 sm:grid-cols-2 gap-4"
            >
              <div className="rounded-xl p-5 border border-white/5 bg-black/20">
                <p className="font-mono text-[10px] uppercase tracking-wider opacity-40 mb-3 flex items-center gap-2">
                  <Globe className="h-3 w-3" /> Social Preview
                </p>
                <div className="space-y-2">
                  <p className="font-bold text-sm text-blue-400">{data.seo_metadata.og_title}</p>
                  <p className="text-xs opacity-60 leading-relaxed line-clamp-2">{data.seo_metadata.og_description}</p>
                </div>
              </div>
              <div className="rounded-xl p-5 border border-white/5 bg-black/20">
                <p className="font-mono text-[10px] uppercase tracking-wider opacity-40 mb-3 flex items-center gap-2">
                  <Hash className="h-3 w-3" /> Target Keywords
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {data.seo_metadata.target_keywords.map((kw, i) => (
                    <span key={i} className="px-2 py-0.5 rounded text-[10px] bg-white/5 text-white/50 border border-white/5">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            </motion.div>

            {/* ═══ Social Share Narrative ═══ */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.48 }}
              className="rounded-2xl p-6 border border-white/5 relative overflow-hidden"
              style={{ background: "linear-gradient(135deg, rgba(59,130,246,0.05), rgba(147,197,253,0.02))" }}
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl -mr-10 -mt-10" />
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-blue-400 mb-3 flex items-center gap-2 relative z-10">
                <Globe className="h-3.5 w-3.5" /> LinkedIn Share Narrative
              </p>
              <div className="bg-black/40 p-4 rounded-xl border border-white/5 relative z-10">
                <p className="text-sm italic opacity-85 leading-relaxed text-blue-100">
                  "{data.social_share_narrative}"
                </p>
              </div>
              <button
                onClick={() => navigator.clipboard.writeText(data.social_share_narrative)}
                className="mt-3 text-xs font-bold text-blue-400 hover:text-blue-300 transition-colors uppercase tracking-widest relative z-10"
              >
                Copy to Clipboard
              </button>
            </motion.div>

            {/* ═══ Snap-Resume Toggle & Export ═══ */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={handleExport}
                  disabled={isExporting}
                  className="w-full sm:flex-1 py-4 rounded-xl border border-indigo-500/20 bg-indigo-500/10 hover:bg-indigo-500/20 transition-colors flex items-center justify-center gap-2 font-mono text-xs uppercase tracking-widest text-indigo-300 disabled:opacity-50"
                >
                  {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  Export Premium PDF
                </button>
                <button
                  onClick={() => setShowResume(!showResume)}
                  className="w-full sm:flex-1 py-4 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors flex items-center justify-center gap-2 font-mono text-xs uppercase tracking-widest text-white/70"
                >
                  {showResume ? "Hide Snap-Resume" : "View Snap-Resume (HTML)"}
                </button>
              </div>
              
              <AnimatePresence>
                {showResume && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden mt-4"
                  >
                    <div className="p-6 rounded-xl border border-white/10 bg-[#0f172a] prose prose-invert max-w-none text-sm"
                         dangerouslySetInnerHTML={{ __html: data.resume_html }} 
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            {/* ═══ Career Coach Chat ═══ */}
            <div className="mt-6 border-t border-white/5 pt-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-blue-400" />
                TalentForge Agent
                <span className="text-[10px] font-mono opacity-30 ml-auto">INTERACTIVE</span>
              </h3>
              <div className="rounded-2xl border border-white/5 overflow-hidden flex flex-col h-[280px]"
                style={{ background: "rgba(0,0,0,0.3)" }}
              >
                <div className="flex-1 overflow-y-auto p-4 space-y-3 flex flex-col">
                  {chatMessages.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center">
                      <p className="text-center text-white/25 text-sm font-mono">
                        Ask how to execute the Gap-Closer blueprint or optimize your resume.
                      </p>
                    </div>
                  ) : (
                    chatMessages.map((msg, i) => (
                      <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                          msg.role === "user"
                            ? "bg-indigo-600 text-white"
                            : "bg-white/5 text-white/85 border border-white/5"
                        }`}>
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    ))
                  )}
                  {isTyping && (
                    <div className="flex justify-start">
                      <div className="bg-white/5 border border-white/5 rounded-2xl px-4 py-2.5 flex gap-2 items-center">
                        <Loader2 className="w-4 h-4 animate-spin opacity-40" />
                        <span className="text-sm opacity-40 font-mono">analyzing...</span>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>
                <div className="p-3 border-t border-white/5 bg-black/40 flex gap-2">
                  <input
                    type="text"
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask for actionable career advice..."
                    className="flex-1 bg-transparent border border-white/8 rounded-xl text-sm px-4 py-2.5 outline-none transition-all placeholder:text-white/20 focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={isTyping || !currentMessage.trim()}
                    className="px-4 bg-indigo-500 rounded-xl hover:bg-indigo-400 disabled:opacity-30 disabled:hover:bg-indigo-500 transition-all text-white flex items-center justify-center"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

        </div>
      </motion.div>
    </AnimatePresence>
  );
}
