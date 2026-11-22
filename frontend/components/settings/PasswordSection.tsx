'use client';

import { Card, CardContent, FormField } from '@/components/ui';
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
}: Readonly<PasswordSectionProps>) {
  return (
    <Card>
      <CardContent>
        <div className="mb-6">
          <h2 className="text-foreground text-xl font-semibold">Password</h2>
          <p className="text-foreground-muted mt-1 text-sm">
            {hasPassword ? 'Change your password' : 'Add an email password to your account'}
          </p>
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
