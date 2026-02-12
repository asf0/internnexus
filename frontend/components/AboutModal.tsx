"use client";

import Modal from "./Modal";

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AboutModal({ isOpen, onClose }: AboutModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="About" size="lg">
      <div className="space-y-6">
        <div>
          <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
            InternNexus
          </h3>
          <p className="text-slate-600 dark:text-slate-400">
            Smart Job Matching Platform
          </p>
        </div>
        
        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          <p className="text-sm text-slate-500 dark:text-slate-500">
            Built by asf0
          </p>
        </div>
        
        <div>
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Tech Stack
          </h4>
          <div className="flex flex-wrap gap-2">
            {["FastAPI", "Next.js", "PostgreSQL", "Redis", "Docker"].map((tech) => (
              <span
                key={tech}
                className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700 dark:bg-slate-800 dark:text-slate-300"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
        
        <div>
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Features
          </h4>
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-md-primary"></span>
              15k+ jobs from 145+ companies
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-md-primary"></span>
              Smart resume matching using AI embeddings
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-md-primary"></span>
              Real-time job aggregation
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-md-primary"></span>
              Personalized recommendations
            </li>
          </ul>
        </div>
      </div>
    </Modal>
  );
}
