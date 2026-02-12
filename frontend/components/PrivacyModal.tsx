"use client";

import Modal from "./Modal";

interface PrivacyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PrivacyModal({ isOpen, onClose }: PrivacyModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Privacy" size="lg">
      <div className="space-y-4">
        <p className="text-slate-600 dark:text-slate-400">
          We collect minimal data for job matching only. Your information is never sold to third parties.
        </p>
        
        <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
          <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
            Data We Collect
          </h4>
          <ul className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
            <li>• Email address (for account)</li>
            <li>• Resume text (for matching, optional)</li>
            <li>• Profile preferences (optional)</li>
          </ul>
        </div>
        
        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          <p className="text-xs text-slate-500 dark:text-slate-500">
            Last updated: 2026
          </p>
        </div>
      </div>
    </Modal>
  );
}
