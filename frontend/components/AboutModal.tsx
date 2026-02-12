"use client";

import Modal from "./Modal";
import { Badge, Card, CardContent } from "./ui";

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AboutModal({ isOpen, onClose }: AboutModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="About" size="lg">
      <div className="space-y-6">
        <div>
          <h3 className="mb-2 text-lg font-semibold text-slate-900 dark:text-md-on-surface">
            InternNexus
          </h3>
          <p className="text-slate-600 dark:text-md-on-surface-variant">
            Smart Job Matching Platform
          </p>
        </div>
        
        <Card>
          <CardContent>
            <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">
              Built by asf0
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent>
            <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-md-on-surface-variant">
              Tech Stack
            </h4>
            <div className="flex flex-wrap gap-2">
              {["FastAPI", "Next.js", "PostgreSQL", "Redis", "Docker"].map((tech) => (
                <Badge key={tech} variant="default">
                  {tech}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent>
            <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-md-on-surface-variant">
              Features
            </h4>
            <ul className="space-y-2 text-sm text-slate-600 dark:text-md-on-surface-variant">
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
          </CardContent>
        </Card>
      </div>
    </Modal>
  );
}
