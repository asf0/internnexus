"use client";

import { Button } from "@/components/ui";
import { X, Check, XCircle, Trash2 } from "lucide-react";
import { Popconfirm } from "antd";

interface BulkActionsBarProps {
  selectedCount: number;
  onActivate: () => void;
  onDeactivate: () => void;
  onDelete: () => void;
  onClear: () => void;
}

export function BulkActionsBar({
  selectedCount,
  onActivate,
  onDeactivate,
  onDelete,
  onClear,
}: BulkActionsBarProps) {
  if (selectedCount === 0) {
    return null;
  }

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 animate-slide-up"
    >
      <div className="bg-md-surface-container-high dark:bg-md-surface-container-high border-t border-md-outline-variant shadow-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-4">
            {/* Selected count */}
            <div className="flex items-center gap-3 shrink-0">
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-md-primary text-white text-sm font-semibold">
                {selectedCount}
              </span>
              <span className="text-sm font-medium text-md-on-surface">
                {selectedCount === 1 ? "item" : "items"} selected
              </span>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 sm:gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={onActivate}
                className="text-green-600 dark:text-green-400 border-green-300 dark:border-green-700 hover:bg-green-50 dark:hover:bg-green-900/20"
              >
                <Check className="w-4 h-4" />
                <span className="hidden sm:inline">Activate</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={onDeactivate}
                className="text-amber-600 dark:text-amber-400 border-amber-300 dark:border-amber-700 hover:bg-amber-50 dark:hover:bg-amber-900/20"
              >
                <XCircle className="w-4 h-4" />
                <span className="hidden sm:inline">Deactivate</span>
              </Button>

              <Popconfirm
                title={`Delete ${selectedCount} ${selectedCount === 1 ? "item" : "items"}?`}
                description="This action cannot be undone."
                onConfirm={onDelete}
                okText="Yes, delete"
                cancelText="Cancel"
                okButtonProps={{ danger: true }}
              >
                <Button
                  variant="outline"
                  size="sm"
                  className="text-red-600 dark:text-red-400 border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="w-4 h-4" />
                  <span className="hidden sm:inline">Delete</span>
                </Button>
              </Popconfirm>

              {/* Divider */}
              <div className="w-px h-8 bg-md-outline-variant mx-1" />

              {/* Clear selection */}
              <Button
                variant="ghost"
                size="sm"
                onClick={onClear}
                className="text-md-on-surface-variant hover:text-md-on-surface"
                aria-label="Clear selection"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-up {
          from {
            transform: translateY(100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out forwards;
        }
      `}</style>
    </div>
  );
}
