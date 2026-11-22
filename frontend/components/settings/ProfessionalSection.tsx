'use client';

import { useRef } from 'react';
import { Plus, X } from 'lucide-react';
import { Card, CardContent, FormField, Input, Badge, Button } from '@/components/ui';

interface ProfessionalSectionProps {
  readonly jobTitle: string;
  readonly company: string;
  readonly industry: string;
  readonly linkedinUrl: string;
  readonly portfolioUrl: string;
  readonly skills: ReadonlyArray<string>;
  readonly preferredLocations: ReadonlyArray<string>;
  readonly onFieldChange: (field: string, value: string) => void;
  readonly onAddSkill: (skill: string) => void;
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
}: Readonly<ProfessionalSectionProps>) {
  const skillInputRef = useRef<HTMLInputElement>(null);
  const locationInputRef = useRef<HTMLInputElement>(null);

  const addInputValue = (input: HTMLInputElement | null, addValue: (value: string) => void) => {
    if (!input?.value) return;
    addValue(input.value);
    input.value = '';
    input.focus();
  };

  return (
    <Card>
      <CardContent>
        <div className="mb-6">
          <h2 className="text-foreground text-xl font-semibold">Professional Information</h2>
          <p className="text-foreground-muted mt-1 text-sm">
            Information used to personalize your job search
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <FormField
            label="Job Title"
            value={jobTitle}
            onChange={(value) => onFieldChange('job_title', value)}
            placeholder="Software Engineer"
          />

          <FormField
            label="Company"
            value={company}
            onChange={(value) => onFieldChange('company', value)}
            placeholder="Acme Inc."
          />

          <FormField
            label="Industry"
            value={industry}
            onChange={(value) => onFieldChange('industry', value)}
            placeholder="Technology"
          />

          <FormField
            label="LinkedIn URL"
            value={linkedinUrl}
            onChange={(value) => onFieldChange('linkedin_url', value)}
            placeholder="https://linkedin.com/in/username"
          />

          <div className="md:col-span-2">
            <FormField
              label="Portfolio / Website"
              value={portfolioUrl}
              onChange={(value) => onFieldChange('portfolio_url', value)}
              placeholder="https://yourportfolio.com"
            />
          </div>
        </div>

        <div className="mt-6">
          <label
            htmlFor="profile-skill"
            className="text-foreground-secondary mb-2 block text-sm font-medium"
          >
            Skills
          </label>
          <div className="mb-2 flex flex-wrap gap-2">
            {skills.map((skill) => (
              <Badge key={skill} variant="outline">
                {skill}
                <button
                  type="button"
                  aria-label={`Remove ${skill}`}
                  onClick={() => onRemoveSkill(skill)}
                  className="hover:text-foreground focus-visible:ring-focus-ring ml-1 rounded-full focus-visible:ring-2 focus-visible:outline-none"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              ref={skillInputRef}
              id="profile-skill"
              type="text"
              placeholder="Add a skill (e.g., Python, React)"
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addInputValue(e.currentTarget, onAddSkill);
                }
              }}
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => addInputValue(skillInputRef.current, onAddSkill)}
            >
              <Plus className="h-5 w-5" />
              Add
            </Button>
          </div>
        </div>

        <div className="mt-6">
          <label
            htmlFor="profile-preferred-location"
            className="text-foreground-secondary mb-2 block text-sm font-medium"
          >
            Preferred Job Locations
          </label>
          <div className="mb-2 flex flex-wrap gap-2">
            {preferredLocations.map((location) => (
              <Badge key={location} variant="outline">
                {location}
                <button
                  type="button"
                  aria-label={`Remove ${location}`}
                  onClick={() => onRemoveLocation(location)}
                  className="hover:text-foreground focus-visible:ring-focus-ring ml-1 rounded-full focus-visible:ring-2 focus-visible:outline-none"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              ref={locationInputRef}
              id="profile-preferred-location"
              type="text"
              placeholder="Add a location (e.g., San Francisco, Remote)"
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addInputValue(e.currentTarget, onAddLocation);
                }
              }}
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={() => addInputValue(locationInputRef.current, onAddLocation)}
            >
              <Plus className="h-5 w-5" />
              Add
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
