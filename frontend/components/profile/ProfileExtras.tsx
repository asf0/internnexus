'use client';

import Link from 'next/link';
import { useRef, useState } from 'react';
import {
  clearAllNotifications,
  deleteNotification,
  deleteUserResume,
  markAllNotificationsRead,
  markNotificationRead,
  uploadUserResume,
} from '@/app/actions/user';
import { Alert } from '@/components/ui';
import type { NotificationItem, SavedJobRecord, UserResume } from '@/lib/types/user';

interface ProfileExtrasProps {
  initialResume: UserResume | null;
  resumeLoadError?: string;
  initialNotifications: NotificationItem[];
  initialSavedJobs: SavedJobRecord[];
}

function formatNotificationPayload(payload: Record<string, unknown>): string {
  const preferredKeys = ['message', 'file_name', 'job_title', 'company', 'status'];
  for (const key of preferredKeys) {
    const value = payload[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      return value;
    }
  }

  const parts = Object.entries(payload)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`);
  if (parts.length > 0) return parts.join(' | ');

  const fallback = JSON.stringify(payload);
  return fallback.length > 140 ? `${fallback.slice(0, 140)}...` : fallback;
}

function formatNotificationType(type: string): string {
  return type
    .split(/[._-]/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ');
}

function resumeStatusLabel(status: string, hasEmbedding: boolean): string {
  if (status === 'error') return 'Needs attention';
  if (status === 'processing') return 'Processing';
  if (hasEmbedding) return 'Ready for matching';
  return 'Uploaded';
}

export default function ProfileExtras({
  initialResume,
  resumeLoadError,
  initialNotifications,
  initialSavedJobs,
}: Readonly<ProfileExtrasProps>) {
  const [resume, setResume] = useState<UserResume | null>(initialResume);
  const [notifications, setNotifications] = useState<NotificationItem[]>(initialNotifications);
  const [savedJobs] = useState<SavedJobRecord[]>(initialSavedJobs);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>('');
  const [selectedResumeName, setSelectedResumeName] = useState<string>('');
  const [showClearAllConfirm, setShowClearAllConfirm] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const hasUnreadNotifications = notifications.some((notification) => !notification.is_read);
  const messageIsError =
    message.toLowerCase().includes('failed') || message.toLowerCase().includes('error');

  const onResumeUpload = async (file: File | null) => {
    if (!file) return;
    setSelectedResumeName(file.name);
    setBusy(true);
    setMessage('Uploading resume and generating embedding...');
    const result = await uploadUserResume(file);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (!result.success || !result.data) {
      setMessage(result.error || 'Failed to upload resume.');
      setBusy(false);
      return;
    }
    setSelectedResumeName('');
    setResume(result.data);
    setMessage('Resume metadata updated.');
    setBusy(false);
  };

  const onResumeDelete = async () => {
    setBusy(true);
    setMessage('');
    const result = await deleteUserResume();
    if (!result.success) {
      setMessage(result.error || 'Failed to delete resume.');
      setBusy(false);
      return;
    }
    setResume(null);
    setMessage('Resume removed.');
    setBusy(false);
  };

  const onReadNotification = async (id: string) => {
    const result = await markNotificationRead(id);
    if (!result.success) {
      setMessage(result.error || 'Failed to mark notification.');
      return;
    }
    setNotifications((prev) =>
      prev.map((row) => (row.id === id ? { ...row, is_read: true } : row))
    );
  };

  const onReadAll = async () => {
    const result = await markAllNotificationsRead();
    if (!result.success) {
      setMessage(result.error || 'Failed to mark all notifications.');
      return;
    }
    setNotifications((prev) => prev.map((row) => ({ ...row, is_read: true })));
  };

  const onDeleteNotification = async (id: string) => {
    const result = await deleteNotification(id);
    if (!result.success) {
      setMessage(result.error || 'Failed to delete notification.');
      return;
    }
    setNotifications((prev) => prev.filter((row) => row.id !== id));
  };

  const onClearAll = async () => {
    setShowClearAllConfirm(false);
    const result = await clearAllNotifications();
    if (!result.success) {
      setMessage(result.error || 'Failed to clear notifications.');
      return;
    }
    setNotifications([]);
  };

  return (
    <div className="space-y-6">
      {message && (
        <div role="status" aria-live="polite">
          <Alert type={messageIsError ? 'error' : 'success'}>{message}</Alert>
        </div>
      )}

      <div className="border-border bg-surface rounded-xl border p-6 shadow-sm">
        <h3 className="text-foreground mb-3 text-lg font-semibold">Resume</h3>
        {resume ? (
          <div className="border-border bg-surface-subtle mb-4 rounded-lg border p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-foreground truncate text-sm font-medium">{resume.file_name}</p>
              <span className="border-border bg-surface text-foreground-secondary rounded-full border px-2.5 py-1 text-xs font-medium">
                {resumeStatusLabel(resume.status, resume.has_embedding)}
              </span>
            </div>
            <p className="text-foreground-muted mt-2 text-xs">
              Uploaded{' '}
              <time dateTime={resume.uploaded_at}>
                {new Date(resume.uploaded_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
              </time>
            </p>
            {resume.embedding_error && (
              <p className="text-danger mt-2 text-sm">
                We could not prepare this resume for matching. Try uploading it again.
              </p>
            )}
          </div>
        ) : (
          <div className="mb-3">
            <p className="text-foreground-secondary text-sm">No resume uploaded yet.</p>
            {resumeLoadError && (
              <p className="text-danger mt-2 text-sm">Resume service error: {resumeLoadError}</p>
            )}
          </div>
        )}
        <div className="flex flex-wrap gap-3">
          {!resume && (
            <div className="w-full space-y-2">
              <label
                htmlFor="resume-upload"
                className={`inline-flex items-center rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  busy
                    ? 'border-border text-foreground-muted cursor-not-allowed'
                    : 'border-accent text-accent hover:bg-surface-subtle cursor-pointer'
                }`}
              >
                {busy ? 'Uploading...' : 'Upload Resume (PDF or TXT)'}
              </label>
              <input
                id="resume-upload"
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt"
                disabled={busy}
                onChange={(event) => onResumeUpload(event.target.files?.[0] || null)}
                className="sr-only"
              />
              <p className="text-foreground-muted text-xs">
                {selectedResumeName
                  ? `Selected: ${selectedResumeName}`
                  : 'Max size 10MB. Your resume is used for better job matching.'}
              </p>
            </div>
          )}
          {resume && (
            <button
              type="button"
              disabled={busy}
              onClick={onResumeDelete}
              className="border-danger text-danger hover:bg-surface-subtle rounded-lg border px-3 py-2 text-sm"
            >
              Remove Resume
            </button>
          )}
        </div>
      </div>

      <div id="notifications" className="border-border bg-surface rounded-xl border p-6 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-foreground text-lg font-semibold">Notifications</h3>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onReadAll}
              disabled={!hasUnreadNotifications}
              className="text-accent disabled:text-foreground-muted text-sm hover:underline disabled:cursor-not-allowed disabled:no-underline"
            >
              Mark all as read
            </button>
            {notifications.length > 0 && (
              <button
                type="button"
                onClick={() => setShowClearAllConfirm(true)}
                className="text-danger text-sm hover:underline"
              >
                Clear all
              </button>
            )}
          </div>
        </div>
        {showClearAllConfirm && (
          <div className="border-border bg-surface-subtle mb-3 flex items-center gap-4 rounded-lg border px-4 py-3 text-sm">
            <span className="text-foreground-secondary">Delete all notifications?</span>
            <button
              type="button"
              onClick={onClearAll}
              className="bg-danger text-on-accent rounded-md px-3 py-1.5 text-xs font-medium opacity-90 hover:opacity-100"
            >
              Clear all
            </button>
            <button
              type="button"
              onClick={() => setShowClearAllConfirm(false)}
              className="text-foreground-muted hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        )}
        <div className="space-y-2">
          {notifications.length === 0 && (
            <p className="text-foreground-secondary text-sm">No notifications.</p>
          )}
          {notifications.map((row) => (
            <div
              key={row.id}
              className={`rounded border p-3 text-sm ${
                row.is_read
                  ? 'border-border bg-surface text-foreground-secondary'
                  : 'border-border border-l-accent bg-surface-subtle text-foreground border-l-4'
              }`}
            >
              <div className="text-foreground font-medium">{formatNotificationType(row.type)}</div>
              <div className="text-foreground-secondary mt-1 text-xs">
                {formatNotificationPayload(row.payload)}
              </div>
              <div className="mt-2 flex items-center gap-3">
                {!row.is_read && (
                  <button
                    type="button"
                    onClick={() => onReadNotification(row.id)}
                    className="text-accent text-xs hover:underline"
                  >
                    Mark as read
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onDeleteNotification(row.id)}
                  className="text-danger text-xs hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border-border bg-surface rounded-xl border p-6 shadow-sm">
        <h3 className="text-foreground mb-3 text-lg font-semibold">Saved Jobs</h3>
        {savedJobs.length === 0 ? (
          <p className="text-foreground-secondary text-sm">No saved jobs yet.</p>
        ) : (
          <div className="space-y-2">
            {savedJobs.slice(0, 20).map((row) => (
              <Link
                key={row.id}
                href={`/jobs/${row.job.id}`}
                className="border-border hover:bg-surface-subtle block rounded-lg border p-3"
              >
                <div className="text-foreground text-sm font-medium">{row.job.title}</div>
                <div className="text-foreground-secondary text-xs">
                  {row.job.company} • {row.job.location}
                </div>
              </Link>
            ))}
            <Link
              href="/?saved_only=1"
              className="text-foreground-secondary decoration-border inline-block pt-2 text-sm font-medium underline underline-offset-4"
            >
              View all saved jobs
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
