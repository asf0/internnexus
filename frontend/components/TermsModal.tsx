"use client";

import Modal from "./Modal";

interface TermsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function TermsModal({ isOpen, onClose }: TermsModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Terms" size="lg">
      <div className="space-y-4">
        <p className="text-slate-600 dark:text-md-on-surface-variant">
          This platform is for educational and demonstration purposes.
        </p>
        
        <div className="rounded-lg bg-slate-50 p-4 dark:bg-md-surface-container-high">
          <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-md-on-surface">
            Usage
          </h4>
          <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">
            By using this service, you agree that this is a demo project showcasing modern web development techniques.
          </p>
        </div>
        
        <div className="border-t border-slate-200 pt-4 dark:border-md-outline-variant">
          <p className="text-xs text-slate-500 dark:text-md-on-surface-variant">
            Last updated: 2026
          </p>
        </div>
      </div>
    </Modal>
  );
}
