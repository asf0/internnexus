import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import GlobalError from '@/app/global-error';

describe('GlobalError', () => {
  it('renders the catastrophe recovery path with global styles loaded', () => {
    render(
      <GlobalError
        error={Object.assign(new Error('boom'), { digest: 'error-123' })}
        reset={vi.fn()}
      />
    );

    expect(screen.getByRole('heading', { name: /couldn't load InternNexus/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    expect(screen.getByText(/error-123/i)).toBeInTheDocument();
  });
});
