"use client";

import { useRef, useState } from "react";
import {
  deleteUserResume,
  markAllNotificationsRead,
  markNotificationRead,
  uploadUserResume,
} from "@/app/actions/user";
import type { NotificationItem, SavedJobRecord, UserResume } from "@/lib/types/user";

interface ProfileExtrasProps {
  initialResume: UserResume | null;
  resumeLoadError?: string;
  initialNotifications: NotificationItem[];
  initialSavedJobs: SavedJobRecord[];
}

function formatNotificationPayload(payload: Record<string, unknown>): string {
  const preferredKeys = ["message", "file_name", "job_title", "company", "status"];
  for (const key of preferredKeys) {
    const value = payload[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }
  }

  const parts = Object.entries(payload)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`);
  if (parts.length > 0) return parts.join(" | ");

  const fallback = JSON.stringify(payload);
  return fallback.length > 140 ? `${fallback.slice(0, 140)}...` : fallback;
}

export default function ProfileExtras({
  initialResume,
  resumeLoadError,
  initialNotifications,
  initialSavedJobs,
}: ProfileExtrasProps) {
  const [resume, setResume] = useState<UserResume | null>(initialResume);
  const [notifications, setNotifications] = useState<NotificationItem[]>(initialNotifications);
  const [savedJobs] = useState<SavedJobRecord[]>(initialSavedJobs);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [selectedResumeName, setSelectedResumeName] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const onResumeUpload = async (file: File | null) => {
    if (!file) return;
    setSelectedResumeName(file.name);
    setBusy(true);
    setMessage("Uploading resume and generating embedding...");
    const result = await uploadUserResume(file);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    if (!result.success || !result.data) {
      setMessage(result.error || "Failed to upload resume.");
      setBusy(false);
      return;
    }
    setSelectedResumeName("");
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
            <div>Embedding: {resume.has_embedding ? "Ready" : "Not ready"}</div>
            {resume.embedding_model && <div>Model: {resume.embedding_model}</div>}
            {resume.last_embedded_at && (
              <div>Last embedded: {new Date(resume.last_embedded_at).toLocaleString()}</div>
            )}
            {resume.embedding_error && (
              <div className="text-red-600">Embedding error: {resume.embedding_error}</div>
            )}
          </div>
        ) : (
          <div className="mb-3">
            <p className="text-sm text-slate-600 dark:text-md-on-surface-variant">
              No resume uploaded yet.
            </p>
            {resumeLoadError && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                Resume service error: {resumeLoadError}
              </p>
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
                    ? "cursor-not-allowed border-slate-200 text-slate-400 dark:border-md-outline-variant dark:text-md-on-surface-variant"
                    : "cursor-pointer border-blue-300 text-blue-700 hover:bg-blue-50 dark:border-blue-600 dark:text-blue-400 dark:hover:bg-blue-950/30"
                }`}
              >
                {busy ? "Uploading..." : "Upload Resume (PDF or TXT)"}
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
              <p className="text-xs text-slate-500 dark:text-md-on-surface-variant">
                {selectedResumeName
                  ? `Selected: ${selectedResumeName}`
                  : "Max size 10MB. Your resume is used for better job matching."}
              </p>
            </div>
          )}
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
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
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
                row.is_read
                  ? "border-slate-200 dark:border-md-outline-variant bg-white dark:bg-md-surface-container text-slate-600 dark:text-md-on-surface-variant"
                  : "border-slate-200 dark:border-md-outline-variant border-l-4 border-l-blue-500 bg-white dark:bg-md-surface-container-high text-slate-800 dark:text-md-on-surface"
              }`}
            >
              <div className="font-medium text-slate-900 dark:text-md-on-surface">{row.type}</div>
              <div className="text-xs mt-1 text-slate-600 dark:text-md-on-surface-variant">
                {formatNotificationPayload(row.payload)}
              </div>
              {!row.is_read && (
                <button
                  type="button"
                  onClick={() => onReadNotification(row.id)}
                  className="mt-2 text-xs text-blue-700 dark:text-blue-400 hover:underline"
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

      {message && (
        <p
          className={`text-sm ${
            message.toLowerCase().includes("failed") || message.toLowerCase().includes("error")
              ? "text-red-600 dark:text-red-400"
              : "text-slate-700 dark:text-md-on-surface-variant"
          }`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
