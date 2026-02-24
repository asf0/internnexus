"use client";

import { useState } from "react";
import {
  deleteUserResume,
  markAllNotificationsRead,
  markNotificationRead,
  uploadUserResume,
} from "@/app/actions/user";
import type { NotificationItem, SavedJobRecord, UserResume } from "@/lib/types/user";

interface ProfileExtrasProps {
  initialResume: UserResume | null;
  initialNotifications: NotificationItem[];
  initialSavedJobs: SavedJobRecord[];
}

export default function ProfileExtras({
  initialResume,
  initialNotifications,
  initialSavedJobs,
}: ProfileExtrasProps) {
  const [resume, setResume] = useState<UserResume | null>(initialResume);
  const [notifications, setNotifications] = useState<NotificationItem[]>(initialNotifications);
  const [savedJobs] = useState<SavedJobRecord[]>(initialSavedJobs);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>("");

  const onResumeUpload = async (file: File | null) => {
    if (!file) return;
    setBusy(true);
    setMessage("");
    const result = await uploadUserResume(file);
    if (!result.success || !result.data) {
      setMessage(result.error || "Failed to upload resume.");
      setBusy(false);
      return;
    }
    setResume(result.data);
    setMessage("Resume metadata updated.");
    setBusy(false);
  };

  const onResumeDelete = async () => {
    setBusy(true);
    setMessage("");
    const result = await deleteUserResume();
    if (!result.success) {
      setMessage(result.error || "Failed to delete resume.");
      setBusy(false);
      return;
    }
    setResume(null);
    setMessage("Resume removed.");
    setBusy(false);
  };

  const onReadNotification = async (id: string) => {
    const result = await markNotificationRead(id);
    if (!result.success) {
      setMessage(result.error || "Failed to mark notification.");
      return;
    }
    setNotifications((prev) =>
      prev.map((row) => (row.id === id ? { ...row, is_read: true } : row))
    );
  };

  const onReadAll = async () => {
    const result = await markAllNotificationsRead();
    if (!result.success) {
      setMessage(result.error || "Failed to mark all notifications.");
      return;
    }
    setNotifications((prev) => prev.map((row) => ({ ...row, is_read: true })));
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface mb-3">
          Resume
        </h3>
        {resume ? (
          <div className="text-sm text-slate-700 dark:text-md-on-surface-variant mb-3">
            <div>File: {resume.file_name}</div>
            <div>Status: {resume.status}</div>
            <div>Hash: {resume.file_hash.slice(0, 12)}...</div>
          </div>
        ) : (
          <p className="text-sm text-slate-600 dark:text-md-on-surface-variant mb-3">
            No resume uploaded yet.
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <input
            type="file"
            accept=".pdf,.txt"
            disabled={busy}
            onChange={(event) => onResumeUpload(event.target.files?.[0] || null)}
            className="text-sm"
          />
          {resume && (
            <button
              type="button"
              disabled={busy}
              onClick={onResumeDelete}
              className="px-3 py-2 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50"
            >
              Remove Resume
            </button>
          )}
        </div>
      </div>

      <div id="notifications" className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface">
            Notifications
          </h3>
          <button
            type="button"
            onClick={onReadAll}
            className="text-sm text-blue-600 hover:underline"
          >
            Mark all as read
          </button>
        </div>
        <div className="space-y-2">
          {notifications.length === 0 && (
            <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">
              No notifications.
            </p>
          )}
          {notifications.map((row) => (
            <div
              key={row.id}
              className={`rounded border p-3 text-sm ${
                row.is_read ? "border-slate-200 text-slate-600" : "border-blue-300 bg-blue-50"
              }`}
            >
              <div className="font-medium">{row.type}</div>
              <div className="text-xs mt-1">{JSON.stringify(row.payload)}</div>
              {!row.is_read && (
                <button
                  type="button"
                  onClick={() => onReadNotification(row.id)}
                  className="mt-2 text-xs text-blue-700 hover:underline"
                >
                  Mark as read
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-md-surface-container rounded-xl shadow-sm border border-slate-200 dark:border-md-outline-variant p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-md-on-surface mb-3">
          Saved Jobs
        </h3>
        {savedJobs.length === 0 ? (
          <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">
            No saved jobs yet.
          </p>
        ) : (
          <div className="space-y-2">
            {savedJobs.slice(0, 20).map((row) => (
              <a
                key={row.id}
                href={`/jobs/${row.job.id}`}
                className="block rounded border border-slate-200 p-3 hover:bg-slate-50"
              >
                <div className="text-sm font-medium text-slate-900">{row.job.title}</div>
                <div className="text-xs text-slate-600">{row.job.company} • {row.job.location}</div>
              </a>
            ))}
          </div>
        )}
      </div>

      {message && <p className="text-sm text-slate-700 dark:text-md-on-surface-variant">{message}</p>}
    </div>
  );
}
