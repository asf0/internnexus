'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Save, Ban, Link as LinkIcon, CheckCircle, Loader2, Trash2 } from 'lucide-react';
import { Button, Input, Alert, LoadingSpinner } from '@/components/ui';
import { SingleSelect } from '@/components/ui/SingleSelect';
import { AdminCard, AdminPopconfirm, AdminSwitch, useAdminMessage } from '@/components/admin/ui';
import { fetchJob, updateJob, deactivateJob, hardDeleteJob } from '@/app/actions/admin';

interface AdminJob {
  id: string;
  source: string;
  title: string;
  company: string;
  location: string;
  city: string | null;
  state: string | null;
  country: string | null;
  apply_url: string;
  description_text: string;
  job_category: string | null;
  job_type: string | null;
  work_mode: string | null;
  posted_at: string | null;
  is_active: boolean;
  click_count: number;
  created_at: string | null;
}

const jobTypeOptions = [
  { label: 'Internship', value: 'internship' },
  { label: 'Full Time', value: 'full_time' },
  { label: 'Part Time', value: 'part_time' },
];

const workModeOptions = [
  { label: 'Remote', value: 'remote' },
  { label: 'Hybrid', value: 'hybrid' },
  { label: 'On Site', value: 'on_site' },
];

export default function AdminJobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const message = useAdminMessage();

  const [job, setJob] = useState<AdminJob | null>(null);
  const [form, setForm] = useState<Partial<AdminJob>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isHardDeleting, setIsHardDeleting] = useState(false);

  useEffect(() => {
    fetchJob(jobId).then((result) => {
      if (result.data) {
        setJob(result.data);
        setForm(result.data);
      } else {
        message.error('Failed to load job');
        router.push('/admin/jobs');
      }
      setIsLoading(false);
    });
  }, [jobId, router, message]);

  const handleChange = <K extends keyof AdminJob>(field: K, value: AdminJob[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title?.trim() || !form.company?.trim()) {
      message.error('Title and company are required');
      return;
    }
    setIsSaving(true);
    const result = await updateJob(jobId, form);
    if (result.data) {
      setJob(result.data);
      setForm(result.data);
      message.success('Job updated successfully');
    } else {
      message.error(result.error || 'Failed to update job');
    }
    setIsSaving(false);
  };

  const handleDeactivate = async () => {
    setIsDeleting(true);
    const result = await deactivateJob(jobId);
    if (result.success) {
      message.success('Job deactivated successfully');
      router.push('/admin/jobs');
    } else {
      message.error(result.error || 'Failed to deactivate job');
    }
    setIsDeleting(false);
  };

  const handleReactivate = async () => {
    setIsSaving(true);
    const result = await updateJob(jobId, { is_active: true });
    if (result.data) {
      setJob(result.data);
      setForm(result.data);
      message.success('Job reactivated successfully');
    } else {
      message.error(result.error || 'Failed to reactivate job');
    }
    setIsSaving(false);
  };

  const handleHardDelete = async () => {
    setIsHardDeleting(true);
    const result = await hardDeleteJob(jobId);
    if (result.success) {
      message.success('Job permanently deleted');
      router.push('/admin/jobs');
    } else {
      message.error(result.error || 'Failed to delete job');
    }
    setIsHardDeleting(false);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="py-24 text-center">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Job not found</h2>
        <Button onClick={() => router.push('/admin/jobs')} className="mt-4">
          Back to Jobs
        </Button>
      </div>
    );
  }

  return (
    <div>
      <Button variant="ghost" onClick={() => router.push('/admin/jobs')} className="mb-4 px-0">
        <ArrowLeft className="h-4 w-4" />
        Back to Jobs
      </Button>

      {!job.is_active && (
        <Alert type="warning" className="mb-4">
          This job is inactive and hidden from users.
        </Alert>
      )}

      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
        {job.title || 'Job Details'}
      </h1>
      {job.company && <p className="text-lg text-slate-600 dark:text-slate-400">{job.company}</p>}

      <form onSubmit={handleSave} className="mt-6 max-w-3xl space-y-6">
        <AdminCard title="Editable Fields">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700">
                Title <span className="text-red-500">*</span>
              </label>
              <Input
                value={form.title ?? ''}
                onChange={(e) => handleChange('title', e.target.value)}
                placeholder="Job title"
              />
            </div>
            <div>
              <label className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700">
                Company <span className="text-red-500">*</span>
              </label>
              <Input
                value={form.company ?? ''}
                onChange={(e) => handleChange('company', e.target.value)}
                placeholder="Company name"
              />
            </div>
            <div>
              <label className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700">
                Location
              </label>
              <Input
                value={form.location ?? ''}
                onChange={(e) => handleChange('location', e.target.value)}
                placeholder="Job location"
              />
            </div>
            <div>
              <label className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700">
                Category
              </label>
              <Input
                value={form.job_category ?? ''}
                onChange={(e) => handleChange('job_category', e.target.value)}
                placeholder="Job category"
              />
            </div>
            <div>
              <label className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700">
                Job Type
              </label>
              <SingleSelect
                options={jobTypeOptions}
                value={form.job_type ?? ''}
                onChange={(value) => handleChange('job_type', value || null)}
                placeholder="Select job type"
              />
            </div>
            <div>
              <label className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700">
                Work Mode
              </label>
              <SingleSelect
                options={workModeOptions}
                value={form.work_mode ?? ''}
                onChange={(value) => handleChange('work_mode', value || null)}
                placeholder="Select work mode"
              />
            </div>
            <div className="flex items-end gap-3 md:col-span-2">
              <AdminSwitch
                checked={form.is_active ?? false}
                onChange={(checked) => handleChange('is_active', checked)}
                checkedChildren="Active"
                unCheckedChildren="Inactive"
              />
              <span className="dark:text-md-on-surface-variant text-sm text-slate-600">
                {form.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        </AdminCard>

        <AdminCard title="Read-only Information">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <span className="dark:text-md-on-surface-variant text-sm text-slate-500">
                Click Count
              </span>
              <p className="dark:text-md-on-surface text-lg font-semibold text-slate-900">
                {job.click_count ?? 0}
              </p>
            </div>
            <div>
              <span className="dark:text-md-on-surface-variant text-sm text-slate-500">
                Posted At
              </span>
              <p className="dark:text-md-on-surface text-slate-900">
                {job.posted_at
                  ? new Date(job.posted_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })
                  : 'N/A'}
              </p>
            </div>
            <div className="md:col-span-2">
              <span className="dark:text-md-on-surface-variant text-sm text-slate-500">
                Apply URL
              </span>
              <div className="mt-1">
                {job.apply_url ? (
                  <a
                    href={job.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400"
                  >
                    <LinkIcon className="h-4 w-4" />
                    {job.apply_url}
                  </a>
                ) : (
                  <span className="dark:text-md-on-surface-variant text-slate-400">N/A</span>
                )}
              </div>
            </div>
            <div className="md:col-span-2">
              <span className="dark:text-md-on-surface-variant text-sm text-slate-500">
                Description
              </span>
              <div className="mt-1 max-h-72 overflow-auto rounded-lg border border-slate-700 bg-[#211F26] p-3 text-slate-100">
                <p className="whitespace-pre-wrap">
                  {job.description_text || 'No description available'}
                </p>
              </div>
            </div>
          </div>
        </AdminCard>

        <hr className="dark:border-md-outline-variant border-slate-200" />

        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            {job.is_active ? (
              <AdminPopconfirm
                title="Deactivate this job?"
                description="This will set the job as inactive."
                onConfirm={handleDeactivate}
                okText="Yes, deactivate"
                cancelText="Cancel"
                okButtonProps={{ danger: true, loading: isDeleting }}
              >
                <Button
                  variant="outline"
                  disabled={isDeleting}
                  className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  {isDeleting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Ban className="h-4 w-4" />
                  )}
                  Deactivate Job
                </Button>
              </AdminPopconfirm>
            ) : (
              <>
                <Button variant="primary" onClick={handleReactivate} disabled={isSaving}>
                  {isSaving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle className="h-4 w-4" />
                  )}
                  Reactivate Job
                </Button>
                <AdminPopconfirm
                  title="Delete this job permanently?"
                  description="Are you sure? This will permanently delete this job and cannot be undone."
                  onConfirm={handleHardDelete}
                  okText="Yes, delete permanently"
                  cancelText="Cancel"
                  okButtonProps={{ danger: true, loading: isHardDeleting }}
                >
                  <Button
                    variant="outline"
                    disabled={isHardDeleting}
                    className="border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    {isHardDeleting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                    Delete Permanently
                  </Button>
                </AdminPopconfirm>
              </>
            )}
          </div>
          <Button type="submit" variant="primary" disabled={isSaving}>
            {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
