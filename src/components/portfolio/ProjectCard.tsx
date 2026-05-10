import { ExternalLink, Star, GitFork } from "lucide-react";
import { motion } from "framer-motion";

export type Project = {
  title: string;
  description: string;
  tags: string[];
  stars?: number;
  forks?: number;
  url?: string;
};

export function ProjectCard({ project, index }: { project: Project; index: number }) {
  return (
    <motion.a
      href={project.url ?? "#"}
      target="_blank"
      rel="noreferrer"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * index, duration: 0.4 }}
      whileHover={{ y: -4 }}
      className="glass group rounded-2xl p-6 flex flex-col h-full transition-shadow hover:shadow-2xl"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-lg leading-tight">{project.title}</h3>
        <ExternalLink
          className="h-4 w-4 opacity-40 group-hover:opacity-100 transition-opacity shrink-0 mt-1"
          style={{ color: "var(--accent-glow)" }}
        />
      </div>

      <p className="mt-2 text-sm opacity-70 line-clamp-4 flex-1">
        {project.description}
      </p>

      <p className="mt-3 text-xs font-medium opacity-75">
        Recruiter-ready impact summary
      </p>

      <div className="mt-4 flex items-center gap-4 text-xs font-mono opacity-60">
        {project.stars !== undefined && (
          <span className="inline-flex items-center gap-1">
            <Star className="h-3 w-3" /> {project.stars}
          </span>
        )}
        {project.forks !== undefined && (
          <span className="inline-flex items-center gap-1">
            <GitFork className="h-3 w-3" /> {project.forks}
          </span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {project.tags.map((t) => (
          <span
            key={t}
            className="font-mono text-[11px] px-2 py-1 rounded-md glass"
            style={{ color: "var(--accent-glow)" }}
          >
            {t}
          </span>
        ))}
      </div>
    </motion.a>
  );
}