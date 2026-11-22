import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  IconButton,
  PageHeader,
  Select,
  Textarea,
} from '@/components/ui';

afterEach(cleanup);

describe('shared UI primitives', () => {
  it('composes a card with semantic headings and descriptions', () => {
    render(
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Manage your information</CardDescription>
          </div>
        </CardHeader>
        <CardContent>Content</CardContent>
      </Card>
    );

    expect(screen.getByRole('heading', { name: 'Profile', level: 2 })).toBeInTheDocument();
    expect(screen.getByText('Manage your information')).toBeInTheDocument();
  });

  it('renders page actions and accessible form controls', async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(
      <>
        <PageHeader
          title="Settings"
          description="Account preferences"
          actions={
            <IconButton label="Save settings" onClick={onAction}>
              S
            </IconButton>
          }
        />
        <label htmlFor="notes">Notes</label>
        <Textarea id="notes" />
        <label htmlFor="duration">Duration</label>
        <Select id="duration" defaultValue="90">
          <option value="90">90 days</option>
        </Select>
      </>
    );

    await user.click(screen.getByRole('button', { name: 'Save settings' }));
    expect(onAction).toHaveBeenCalledOnce();
    expect(screen.getByRole('heading', { name: 'Settings', level: 1 })).toBeInTheDocument();
    expect(screen.getByLabelText('Notes')).toBeInTheDocument();
    expect(screen.getByLabelText('Duration')).toHaveValue('90');
  });
});
