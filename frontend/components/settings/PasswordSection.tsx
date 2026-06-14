'use client';

import { Lock } from 'lucide-react';
import { Card, CardContent, IconContainer, FormField } from '@/components/ui';
import { PasswordInput } from '@/components/common';

interface PasswordSectionProps {
  hasPassword: boolean;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  onCurrentPasswordChange: (value: string) => void;
  onNewPasswordChange: (value: string) => void;
  onConfirmPasswordChange: (value: string) => void;
}

export function PasswordSection({
  hasPassword,
  currentPassword,
  newPassword,
  confirmPassword,
  onCurrentPasswordChange,
  onNewPasswordChange,
  onConfirmPasswordChange,
}: PasswordSectionProps) {
  return (
    <Card>
      <CardContent>
        <div className="mb-6 flex items-center gap-3">
          <IconContainer icon={Lock} color="purple" />
          <div>
            <h2 className="dark:text-md-on-surface text-xl font-semibold text-slate-900">
              Password
            </h2>
            <p className="dark:text-md-on-surface-variant text-sm text-slate-500">
              {hasPassword ? 'Change password' : 'Set password'}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {hasPassword && (
            <FormField
              label="Current Password"
              value={currentPassword}
              onChange={onCurrentPasswordChange}
              type="password"
            />
          )}

          <PasswordInput
            value={newPassword}
            onChange={onNewPasswordChange}
            confirmValue={confirmPassword}
            onConfirmChange={onConfirmPasswordChange}
            showConfirmation={true}
            label="New Password"
            id="new-password"
          />
        </div>
      </CardContent>
    </Card>
  );
}
