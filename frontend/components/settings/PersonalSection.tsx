'use client';

import { User, Phone, MapPin } from 'lucide-react';
import { Card, CardContent, IconContainer, FormField } from '@/components/ui';

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
        <div className="mb-6 flex items-center gap-3">
          <IconContainer icon={User} color="blue" />
          <div>
            <h2 className="dark:text-md-on-surface text-xl font-semibold text-slate-900">
              Personal
            </h2>
            <p className="dark:text-md-on-surface-variant text-sm text-slate-500">
              Your basic info
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <FormField
            label="Full Name"
            value={name}
            onChange={(value) => onChange('name', value)}
            placeholder="John Doe"
          />

          <div>
            <label className="dark:text-md-on-surface-variant mb-1 block text-sm font-medium text-slate-700">
              Bio / About
            </label>
            <textarea
              value={bio}
              onChange={(e) => onChange('bio', e.target.value)}
              rows={3}
              className="dark:border-md-outline-variant focus:ring-md-primary focus:border-md-primary dark:bg-md-surface-container-high dark:text-md-on-surface w-full rounded-lg border border-slate-300 px-3 py-2 focus:ring-2"
              placeholder="Tell us about yourself..."
            />
          </div>

          <FormField
            label="Phone"
            value={phone}
            onChange={(value) => onChange('phone', value)}
            icon={Phone}
            placeholder="+1 (555) 123-4567"
          />

          <FormField
            label="Location"
            value={location}
            onChange={(value) => onChange('location', value)}
            icon={MapPin}
            placeholder="San Francisco, CA"
          />
        </div>
      </CardContent>
    </Card>
  );
}
