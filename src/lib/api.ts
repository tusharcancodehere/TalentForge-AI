import { API_BASE_URL, CareerArchitectResponse } from "./github";

export async function analyzeProfile(username: string): Promise<CareerArchitectResponse> {
  const response = await fetch(`${API_BASE_URL}/api/architect/${encodeURIComponent(username)}`);
  if (!response.ok) {
    if (response.status === 500) {
      throw new Error("Render server timeout. Retrying with deterministic fallback...");
    }
    throw new Error("Failed to analyze profile.");
  }
  return response.json();
}

export async function getGlobalStats(): Promise<{ active: number; total: number }> {
  const response = await fetch(`${API_BASE_URL}/api/stats`);
  if (!response.ok) {
    throw new Error("Failed to fetch global stats");
  }
  return response.json();
}

export async function chatWithCoach(message: string, context: CareerArchitectResponse): Promise<{ response: string }> {
  const payload = {
    architect_data: {
      architect_classification: context.architect_classification,
      grit_score: context.economic_analysis.readiness_score,
      skill_gaps: context.blueprint.the_stack,
    },
    message,
    history: [],
  };
  const response = await fetch(`${API_BASE_URL}/api/coach/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to chat with coach");
  }
  return response.json();
}

export async function exportCV(username: string, resumeHtml: string, architectClassification: string): Promise<Blob> {
  const payload = {
    username,
    resume_html: resumeHtml,
    architect_classification: architectClassification,
  };
  const response = await fetch(`${API_BASE_URL}/api/cv/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to export CV");
  }
  return response.blob();
}
