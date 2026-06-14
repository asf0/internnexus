'use client';

import { Button } from '@/components/ui';
import { X, Check, XCircle, Trash2 } from 'lucide-react';
import { Popconfirm } from 'antd';

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
    <div className="animate-slide-up fixed right-0 bottom-0 left-0 z-50">
      <div className="bg-md-surface-container-high dark:bg-md-surface-container-high border-md-outline-variant border-t shadow-2xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-4">
            {/* Selected count */}
            <div className="flex shrink-0 items-center gap-3">
              <span className="bg-md-primary inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold text-white">
                {selectedCount}
              </span>
              <span className="text-md-on-surface text-sm font-medium">
                {selectedCount === 1 ? 'item' : 'items'} selected
              </span>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 sm:gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={onActivate}
                className="border-green-300 text-green-600 hover:bg-green-50 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-900/20"
              >
                <Check className="h-4 w-4" />
                <span className="hidden sm:inline">Activate</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={onDeactivate}
                className="border-amber-300 text-amber-600 hover:bg-amber-50 dark:border-amber-700 dark:text-amber-400 dark:hover:bg-amber-900/20"
              >
                <XCircle className="h-4 w-4" />
                <span className="hidden sm:inline">Deactivate</span>
              </Button>

              <Popconfirm
                title={`Delete ${selectedCount} ${selectedCount === 1 ? 'item' : 'items'}?`}
                description="This action cannot be undone."
                onConfirm={onDelete}
                okText="Yes, delete"
                cancelText="Cancel"
                okButtonProps={{ danger: true }}
              >
                <Button
                  variant="outline"
                  size="sm"
                  className="border-red-300 text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="h-4 w-4" />
                  <span className="hidden sm:inline">Delete</span>
                </Button>
              </Popconfirm>

              {/* Divider */}
              <div className="bg-md-outline-variant mx-1 h-8 w-px" />

              {/* Clear selection */}
              <Button
                variant="ghost"
                size="sm"
                onClick={onClear}
                className="text-md-on-surface-variant hover:text-md-on-surface"
                aria-label="Clear selection"
              >
                <X className="h-5 w-5" />
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
