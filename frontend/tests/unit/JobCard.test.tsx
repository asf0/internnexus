import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JobCard } from '@/components/jobs/JobCard';
import type { Job } from '@/lib/types/job';

// Clean up DOM after each test
afterEach(() => {
  cleanup();
});

const mockJob: Job = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  source: 'greenhouse',
  title: 'Software Engineer Intern',
  company: 'TechCorp',
  location: 'San Francisco, CA',
  city: 'San Francisco',
  state: 'CA',
  country: 'USA',
  apply_url: 'https://example.com/apply',
  description_text: 'Great internship opportunity',
  job_category: 'software_engineering',
  job_type: 'internship',
  work_mode: 'hybrid',
  posted_at: '2024-01-01T00:00:00Z',
  is_active: true,
};

describe('JobCard', () => {
  it('renders job title and company', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    expect(screen.getByText('Software Engineer Intern')).toBeDefined();
    expect(screen.getByText('TechCorp')).toBeDefined();
  });

  it('renders location', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    expect(screen.getByText('San Francisco, CA')).toBeDefined();
  });

  it('calls onClick when clicked', async () => {
    // Arrange
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<JobCard job={mockJob} isSelected={false} onClick={handleClick} />);

    // Act
    const card = screen.getByRole('button', { name: /view details/i });
    await user.click(card);

    // Assert
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('calls onClick when activated with Enter or Space', async () => {
    // Arrange
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<JobCard job={mockJob} isSelected={false} onClick={handleClick} />);
    const card = screen.getByRole('button', { name: /view details/i });

    // Act & Assert
    card.focus();
    await user.keyboard('{Enter}');
    expect(handleClick).toHaveBeenCalledTimes(1);

    await user.keyboard(' ');
    expect(handleClick).toHaveBeenCalledTimes(2);
  });

  it('shows selected state styling when isSelected is true', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={true} onClick={vi.fn()} />);

    // Assert
    const card = screen.getByRole('button', { name: /view details/i });
    expect(card.className).toContain('border-blue-500');
    expect(card).toHaveAttribute('aria-pressed', 'true');
  });

  it('shows unselected state styling when isSelected is false', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    const card = screen.getByRole('button', { name: /view details/i });
    expect(card.className).toContain('border-slate-200');
    expect(card).toHaveAttribute('aria-pressed', 'false');
  });

  it('displays match percentage when provided', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} matchPercentage={85.5} />);

    // Assert
    expect(screen.getByText('85.5%')).toBeDefined();
  });

  it('does not display match percentage when not provided', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    const percentageElements = screen.queryAllByText(/%/);
    expect(percentageElements.length).toBe(0);
  });

  it('renders job category badge when available', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    expect(screen.getByText('Software Engineering')).toBeDefined();
  });

  it('renders job type badge when available', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    expect(screen.getByText('Internship')).toBeDefined();
  });

  it('renders work mode badge when available', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    expect(screen.getByText('Hybrid')).toBeDefined();
  });

  it('handles job without optional fields', () => {
    // Arrange
    const minimalJob: Job = {
      ...mockJob,
      job_category: null,
      job_type: null,
      work_mode: null,
    };

    // Act
    render(<JobCard job={minimalJob} isSelected={false} onClick={vi.fn()} />);

    // Assert - Should render without crashing
    expect(screen.getByText('Software Engineer Intern')).toBeDefined();
  });

  it('has correct ARIA role and label', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    const card = screen.getByRole('button', {
      name: `View details for ${mockJob.title} at ${mockJob.company}`,
    });
    expect(card).toBeDefined();
    expect(card).toHaveAttribute('tabIndex', '0');
  });
});
