export type GitHubProfile = {
  login: string;
  name: string | null;
  avatar_url: string;
  html_url: string;
  bio: string | null;
  location: string | null;
  blog: string | null;
};

export type GitHubRepo = {
  id: number;
  name: string;
  description: string | null;
  html_url: string;
  language: string | null;
  stargazers_count: number;
  forks_count: number;
};

export async function fetchGitHubUser(
  username: string,
): Promise<{ profile: GitHubProfile; repos: GitHubRepo[] }> {
  const headers = { Accept: "application/vnd.github+json" };

  const [profileRes, reposRes] = await Promise.all([
    fetch(`https://api.github.com/users/${encodeURIComponent(username)}`, { headers }),
    fetch(
      `https://api.github.com/users/${encodeURIComponent(
        username,
      )}/repos?sort=stargazers&per_page=6`,
      { headers },
    ),
  ]);

  if (profileRes.status === 404) {
    throw new Error("GitHub user not found.");
  }
  if (!profileRes.ok) {
    throw new Error(`GitHub API error (${profileRes.status})`);
  }
  if (!reposRes.ok) {
    throw new Error(`GitHub API error (${reposRes.status})`);
  }

  const profile = (await profileRes.json()) as GitHubProfile;
  const repos = (await reposRes.json()) as GitHubRepo[];
  return { profile, repos };
}