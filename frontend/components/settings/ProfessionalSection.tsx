"use client";

import { Briefcase, Building, GraduationCap, Link as LinkIcon, Plus, X } from "lucide-react";
import { Card, CardContent, IconContainer, FormField, Input, Badge, Button } from "@/components/ui";

interface ProfessionalSectionProps {
  jobTitle: string;
  company: string;
  industry: string;
  linkedinUrl: string;
  portfolioUrl: string;
  skills: string[];
  preferredLocations: string[];
  onFieldChange: (field: string, value: string) => void;
  onAddSkill: (skill: string) => void;
  onRemoveSkill: (skill: string) => void;
  onAddLocation: (location: string) => void;
  onRemoveLocation: (location: string) => void;
}

export function ProfessionalSection({
  jobTitle,
  company,
  industry,
  linkedinUrl,
  portfolioUrl,
  skills,
  preferredLocations,
  onFieldChange,
  onAddSkill,
  onRemoveSkill,
  onAddLocation,
  onRemoveLocation,
}: ProfessionalSectionProps) {
  return (
    <Card>
      <CardContent>
        <div className="flex items-center gap-3 mb-6">
          <IconContainer icon={Briefcase} color="green" />
          <div>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-md-on-surface">Professional Information</h2>
            <p className="text-sm text-slate-500 dark:text-md-on-surface-variant">Your work details</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            label="Job Title"
            value={jobTitle}
            onChange={(value) => onFieldChange("job_title", value)}
            icon={Briefcase}
            placeholder="Software Engineer"
          />

          <FormField
            label="Company"
            value={company}
            onChange={(value) => onFieldChange("company", value)}
            icon={Building}
            placeholder="Acme Inc."
          />

          <FormField
            label="Industry"
            value={industry}
            onChange={(value) => onFieldChange("industry", value)}
            icon={GraduationCap}
            placeholder="Technology"
          />

          <FormField
            label="LinkedIn URL"
            value={linkedinUrl}
            onChange={(value) => onFieldChange("linkedin_url", value)}
            icon={LinkIcon}
            placeholder="https://linkedin.com/in/username"
          />

          <div className="md:col-span-2">
            <FormField
              label="Portfolio / Website"
              value={portfolioUrl}
              onChange={(value) => onFieldChange("portfolio_url", value)}
              icon={LinkIcon}
              placeholder="https://yourportfolio.com"
            />
          </div>
        </div>

        <div className="mt-6">
          <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-2">Skills</label>
          <div className="flex flex-wrap gap-2 mb-2">
            {skills.map((skill) => (
              <Badge key={skill} variant="info">
                {skill}
                <button
                  onClick={() => onRemoveSkill(skill)}
                  className="ml-1 hover:text-blue-900 dark:hover:text-blue-100"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              type="text"
              placeholder="Add a skill (e.g., Python, React)"
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onAddSkill((e.target as HTMLInputElement).value);
                  (e.target as HTMLInputElement).value = "";
                }
              }}
            />
            <Button variant="secondary" size="sm" onClick={() => {
              const input = document.querySelector('input[placeholder*="Add a skill"]') as HTMLInputElement;
              if (input?.value) {
                onAddSkill(input.value);
                input.value = "";
              }
            }}>
              <Plus className="h-5 w-5" />
            </Button>
          </div>
        </div>

        <div className="mt-6">
          <label className="block text-sm font-medium text-slate-700 dark:text-md-on-surface-variant mb-2">Preferred Job Locations</label>
          <div className="flex flex-wrap gap-2 mb-2">
            {preferredLocations.map((location) => (
              <Badge key={location} variant="success">
                {location}
                <button
                  onClick={() => onRemoveLocation(location)}
                  className="ml-1 hover:text-green-900 dark:hover:text-green-100"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              type="text"
              placeholder="Add a location (e.g., San Francisco, Remote)"
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  onAddLocation((e.target as HTMLInputElement).value);
                  (e.target as HTMLInputElement).value = "";
                }
              }}
            />
            <Button variant="secondary" size="sm" onClick={() => {
              const input = document.querySelector('input[placeholder*="Add a location"]') as HTMLInputElement;
              if (input?.value) {
                onAddLocation(input.value);
                input.value = "";
              }
            }}>
              <Plus className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
