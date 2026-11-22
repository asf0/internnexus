'use client';

import { Card, CardContent, FormField, Textarea } from '@/components/ui';

interface PersonalSectionProps {
  readonly name: string;
  readonly bio: string;
  readonly phone: string;
  readonly location: string;
  readonly onChange: (field: string, value: string) => void;
}

export function PersonalSection({ name, bio, phone, location, onChange }: PersonalSectionProps) {
  return (
    <Card>
      <CardContent>
        <div className="mb-6">
          <h2 className="text-foreground text-xl font-semibold">Personal</h2>
          <p className="text-foreground-muted mt-1 text-sm">Your basic information</p>
        </div>

        <div className="space-y-4">
          <FormField
            label="Full Name"
            value={name}
            onChange={(value) => onChange('name', value)}
            placeholder="John Doe"
          />

          <div>
            <label
              htmlFor="profile-bio"
              className="text-foreground-secondary mb-1.5 block text-sm font-medium"
            >
              Bio / About
            </label>
            <Textarea
              id="profile-bio"
              value={bio}
              onChange={(e) => onChange('bio', e.target.value)}
              rows={3}
              placeholder="Tell us about yourself..."
            />
          </div>

          <FormField
            label="Phone"
            value={phone}
            onChange={(value) => onChange('phone', value)}
            placeholder="+1 (555) 123-4567"
          />

          <FormField
            label="Location"
            value={location}
            onChange={(value) => onChange('location', value)}
            placeholder="San Francisco, CA"
          />
        </div>
      </CardContent>
    </Card>
  );
}
