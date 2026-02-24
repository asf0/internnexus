"use client";

import { useState, useEffect } from "react";
import { Briefcase, Loader2 } from "lucide-react";
import { Button, Input, SingleSelect, IconContainer, Alert } from "@/components/ui";
import { Modal } from "@/components/modals";
import { createJob, type CreateJobRequest } from "@/app/actions/admin";

interface CreateJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface JobFormData {
  title: string;
  company: string;
  location: string;
  apply_url: string;
  description_text: string;
  job_category: string;
  job_type: string;
  work_mode: string;
}

const initialFormData: JobFormData = {
  title: "",
  company: "",
  location: "",
  apply_url: "",
  description_text: "",
  job_category: "",
  job_type: "",
  work_mode: "",
};

const jobTypeOptions = [
  { value: "internship", label: "Internship" },
  { value: "full_time", label: "Full Time" },
  { value: "part_time", label: "Part Time" },
];

const workModeOptions = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "on_site", label: "On-site" },
];

export default function CreateJobModal({
  isOpen,
  onClose,
  onSuccess,
}: CreateJobModalProps) {
  const [formData, setFormData] = useState<JobFormData>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setFormData(initialFormData);
      setError(null);
    }
  }, [isOpen]);

  const updateField = (field: keyof JobFormData) => (value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    // Validate required fields
    if (
      !formData.title.trim() ||
      !formData.company.trim() ||
      !formData.location.trim() ||
      !formData.apply_url.trim() ||
      !formData.description_text.trim()
    ) {
      setError("Please fill in all required fields");
      return;
    }

    // Validate URL format
    try {
      new URL(formData.apply_url);
    } catch {
      setError("Please enter a valid URL for the apply link");
      return;
    }

    setIsLoading(true);
    setError(null);

    const jobData: CreateJobRequest = {
      title: formData.title.trim(),
      company: formData.company.trim(),
      location: formData.location.trim(),
      apply_url: formData.apply_url.trim(),
      description_text: formData.description_text.trim(),
      job_category: formData.job_category.trim() || undefined,
      job_type: formData.job_type || undefined,
      work_mode: formData.work_mode || undefined,
    };

    const result = await createJob(jobData);

    if (result.data) {
      onClose();
      onSuccess();
    } else {
      setError(result.error || "Failed to create job");
    }

    setIsLoading(false);
  };

  const handleClose = () => {
    if (!isLoading) {
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={
        <div className="flex items-center gap-3">
          <IconContainer icon={Briefcase} color="blue" />
          <span>Create New Job</span>
        </div>
      }
      size="lg"
    >
      <div className="space-y-4">
        {error && <Alert type="error">{error}</Alert>}

        {/* Required Fields Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-md-on-surface uppercase tracking-wide">
            Required Information
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
                Job Title <span className="text-red-500">*</span>
              </label>
              <Input
                type="text"
                value={formData.title}
                onChange={(e) => updateField("title")(e.target.value)}
                placeholder="e.g. Software Engineering Intern"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
                Company <span className="text-red-500">*</span>
              </label>
              <Input
                type="text"
                value={formData.company}
                onChange={(e) => updateField("company")(e.target.value)}
                placeholder="e.g. Acme Corporation"
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
                Location <span className="text-red-500">*</span>
              </label>
              <Input
                type="text"
                value={formData.location}
                onChange={(e) => updateField("location")(e.target.value)}
                placeholder="e.g. San Francisco, CA"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
                Apply URL <span className="text-red-500">*</span>
              </label>
              <Input
                type="url"
                value={formData.apply_url}
                onChange={(e) => updateField("apply_url")(e.target.value)}
                placeholder="https://company.com/apply"
                disabled={isLoading}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
              Description <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.description_text}
              onChange={(e) => updateField("description_text")(e.target.value)}
              placeholder="Enter job description..."
              disabled={isLoading}
              rows={5}
              className="w-full rounded-lg border border-slate-300 dark:border-md-outline-variant bg-white dark:bg-md-surface-container text-sm text-slate-900 dark:text-md-on-surface placeholder-slate-400 dark:placeholder-md-on-surface-variant focus:border-md-primary focus:outline-none focus:ring-1 focus:ring-md-primary disabled:opacity-50 disabled:cursor-not-allowed px-3 py-2.5 resize-none"
            />
          </div>
        </div>

        {/* Optional Fields Section */}
        <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-md-outline-variant">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-md-on-surface uppercase tracking-wide">
            Optional Information
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
                Job Category
              </label>
              <Input
                type="text"
                value={formData.job_category}
                onChange={(e) => updateField("job_category")(e.target.value)}
                placeholder="e.g. Engineering"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
                Job Type
              </label>
              <SingleSelect
                options={jobTypeOptions}
                value={formData.job_type}
                onChange={updateField("job_type")}
                placeholder="Select type"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-1">
                Work Mode
              </label>
              <SingleSelect
                options={workModeOptions}
                value={formData.work_mode}
                onChange={updateField("work_mode")}
                placeholder="Select mode"
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t border-slate-200 dark:border-md-outline-variant">
          <Button
            variant="secondary"
            onClick={handleClose}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={isLoading}
            className="flex-1"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Job"
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
