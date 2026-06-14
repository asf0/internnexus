'use client';

import { useState, useEffect } from 'react';
import Modal from '@/components/modals/Modal';
import { Button, Input } from '@/components/ui';
import { createUser } from '@/app/actions/admin';

interface CreateUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface FormState {
  email: string;
  password: string;
  name: string;
}

export default function CreateUserModal({ isOpen, onClose, onSuccess }: CreateUserModalProps) {
  const [form, setForm] = useState<FormState>({
    email: '',
    password: '',
    name: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setForm({ email: '', password: '', name: '' });
      setError(null);
      setIsLoading(false);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    // Client-side validation
    if (!form.email.trim()) {
      setError('Email is required');
      setIsLoading(false);
      return;
    }

    if (!form.password) {
      setError('Password is required');
      setIsLoading(false);
      return;
    }

    if (form.password.length < 8) {
      setError('Password must be at least 8 characters');
      setIsLoading(false);
      return;
    }

    try {
      const result = await createUser(
        form.email.trim(),
        form.password,
        form.name.trim() || undefined
      );

      if (result.error) {
        setError(result.error);
        setIsLoading(false);
        return;
      }

      // Success - close modal and refresh user list
      onClose();
      onSuccess();
    } catch {
      setError('An unexpected error occurred');
      setIsLoading(false);
    }
  };

  const handleChange = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (error) setError(null);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create User" size="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-900/20">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        <div className="space-y-1">
          <label
            htmlFor="email"
            className="dark:text-md-on-surface text-sm font-medium text-slate-700"
          >
            Email <span className="text-red-500">*</span>
          </label>
          <Input
            id="email"
            type="email"
            value={form.email}
            onChange={handleChange('email')}
            placeholder="user@example.com"
            disabled={isLoading}
            required
          />
        </div>

        <div className="space-y-1">
          <label
            htmlFor="password"
            className="dark:text-md-on-surface text-sm font-medium text-slate-700"
          >
            Password <span className="text-red-500">*</span>
          </label>
          <Input
            id="password"
            type="password"
            value={form.password}
            onChange={handleChange('password')}
            placeholder="Min 8 characters"
            disabled={isLoading}
            required
          />
        </div>

        <div className="space-y-1">
          <label
            htmlFor="name"
            className="dark:text-md-on-surface text-sm font-medium text-slate-700"
          >
            Name <span className="text-slate-400">(optional)</span>
          </label>
          <Input
            id="name"
            type="text"
            value={form.name}
            onChange={handleChange('name')}
            placeholder="John Doe"
            disabled={isLoading}
          />
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isLoading}>
            {isLoading ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
