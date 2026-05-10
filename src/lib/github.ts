export type PortfolioUser = {
  name: string | null;
  avatar_url: string;
  github_url: string;
  bio: string | null;
  location: string | null;
};

export type PortfolioProject = {
  title: string;
  ai_description: string;
  language: string | null;
  stars: number;
  url: string;
};

export type MarketSkillRating = {
  skill: string;
  score: number;
};

export type PortfolioResponse = {
  user: PortfolioUser;
  projects: PortfolioProject[];
  tech_stack: string[];
  market_insights: {
    summary: string;
    selection_probability: number;
    confidence: "Low" | "Medium" | "High";
    recommended_roles: string[];
    market_skill_ratings: MarketSkillRating[];
    avg_package: {
      currency: string;
      min: number;
      max: number;
      period: string;
      note: string;
    };
    strengths: string[];
    gaps: string[];
    action_plan: string[];
    career_growth: {
      current_score: number;
      target_score: number;
      recommended_skills: { skill: string; why: string }[];
      roadmap_summary: string;
    };
  };
  pagination: {
    page: number;
    page_size: number;
    total_projects: number;
    total_pages: number;
  };
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
  || "";

export async function fetchPortfolioData(
  username: string,
  page: number,
  pageSize: number,
): Promise<PortfolioResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/portfolio/${encodeURIComponent(username)}?page=${page}&page_size=${pageSize}`,
  );
  if (response.status === 404) {
    throw new Error("GitHub user not found.");
  }
  if (!response.ok) {
    throw new Error(`Backend API error (${response.status})`);
  }
  return (await response.json()) as PortfolioResponse;
}