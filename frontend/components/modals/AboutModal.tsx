'use client';

import Modal from './Modal';
import { Badge, Card, CardContent } from '@/components/ui';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AboutModal({ isOpen, onClose }: AboutModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="About" size="lg">
      <div className="space-y-6">
        <div>
          <h3 className="dark:text-md-on-surface mb-2 text-lg font-semibold text-slate-900">
            InternNexus
          </h3>
          <p className="dark:text-md-on-surface-variant text-slate-600">
            Smart Job Matching Platform
          </p>
        </div>

        <Card>
          <CardContent>
            <p className="dark:text-md-on-surface-variant text-sm text-slate-500">Built by asf0</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <h4 className="dark:text-md-on-surface-variant mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
              Tech Stack
            </h4>
            <div className="flex flex-wrap gap-2">
              {['FastAPI', 'Next.js', 'PostgreSQL', 'Docker'].map((tech) => (
                <Badge key={tech} variant="default">
                  {tech}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <h4 className="dark:text-md-on-surface-variant mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
              Features
            </h4>
            <ul className="dark:text-md-on-surface-variant space-y-2 text-sm text-slate-600">
              <li className="flex items-center gap-2">
                <span className="bg-md-primary h-1.5 w-1.5 rounded-full"></span>
                15k+ jobs from 145+ companies
              </li>
              <li className="flex items-center gap-2">
                <span className="bg-md-primary h-1.5 w-1.5 rounded-full"></span>
                Smart resume matching using AI embeddings
              </li>
              <li className="flex items-center gap-2">
                <span className="bg-md-primary h-1.5 w-1.5 rounded-full"></span>
                Real-time job aggregation
              </li>
              <li className="flex items-center gap-2">
                <span className="bg-md-primary h-1.5 w-1.5 rounded-full"></span>
                Personalized recommendations
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </Modal>
  );
}
