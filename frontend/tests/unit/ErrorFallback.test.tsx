import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { ErrorFallback } from '@/components/common/ErrorFallback';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('ErrorFallback', () => {
  it('renders the error UI without exposing a stack trace', () => {
    render(<ErrorFallback error={new Error('Boom')} reset={() => {}} />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(
      screen.getByText("We couldn't load this page. You can try again or navigate somewhere safe.")
    ).toBeInTheDocument();
    expect(screen.queryByText('Boom')).not.toBeInTheDocument();
    expect(screen.queryByText(/stack/i)).not.toBeInTheDocument();
  });

  it('calls reset when Try again is clicked', () => {
    const reset = vi.fn();
    render(<ErrorFallback error={new Error('Boom')} reset={reset} />);

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it('navigates home when the home button is clicked', () => {
    const assign = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { href: '', assign },
      writable: true,
    });

    render(
      <ErrorFallback
        error={new Error('Boom')}
        reset={() => {}}
        homeHref="/admin"
        homeLabel="Admin dashboard"
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Admin dashboard' }));
    expect(window.location.href).toBe('/admin');
  });

  it('shows the digest in non-production environments', () => {
    vi.stubEnv('NODE_ENV', 'development');

    render(
      <ErrorFallback
        error={Object.assign(new Error('Boom'), { digest: 'digest-123' })}
        reset={() => {}}
      />
    );

    expect(screen.getByText('Error digest: digest-123')).toBeInTheDocument();
  });

  it('hides the digest in production', () => {
    vi.stubEnv('NODE_ENV', 'production');

    render(
      <ErrorFallback
        error={Object.assign(new Error('Boom'), { digest: 'digest-123' })}
        reset={() => {}}
      />
    );

    expect(screen.queryByText('Error digest: digest-123')).not.toBeInTheDocument();
  });
});
