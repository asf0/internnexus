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
        <p className="text-slate-600 dark:text-slate-400">
          This platform is for educational and demonstration purposes.
        </p>
        
        <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800">
          <h4 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
            Usage
          </h4>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            By using this service, you agree that this is a demo project showcasing modern web development techniques.
          </p>
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
