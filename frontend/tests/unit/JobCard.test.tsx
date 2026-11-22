import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JobCard } from '@/components/jobs/JobCard';
import type { JobSummary } from '@/lib/types/job';

// Clean up DOM after each test
afterEach(() => {
  cleanup();
});

const mockJob: JobSummary = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  source: 'greenhouse',
  title: 'Software Engineer Intern',
  company: 'TechCorp',
  location: 'San Francisco, CA',
  city: 'San Francisco',
  state: 'CA',
  country: 'USA',
  apply_url: 'https://example.com/apply',
  job_category: 'software_engineering',
  job_type: 'internship',
  work_mode: 'hybrid',
  posted_at: '2024-01-01T00:00:00Z',
  is_active: true,
};

type JobCardScenario = {
  readonly name: string;
  readonly verify: (
    user: ReturnType<typeof userEvent.setup>,
    handleClick: ReturnType<typeof vi.fn>
  ) => void | Promise<void>;
};

const basicScenarios: readonly JobCardScenario[] = [
  {
    name: 'renders job title and company',
    verify: () => {
      expect(screen.getByText('Software Engineer Intern')).toBeDefined();
      expect(screen.getByText('TechCorp')).toBeDefined();
    },
  },
  {
    name: 'renders location',
    verify: () => expect(screen.getByText('San Francisco, CA')).toBeDefined(),
  },
  {
    name: 'calls onClick when clicked',
    verify: async (user, handleClick) => {
      await user.click(screen.getByRole('link', { name: mockJob.title }));
      expect(handleClick).toHaveBeenCalledTimes(1);
    },
  },
  {
    name: 'calls onClick when the title link is activated with Enter',
    verify: async (user, handleClick) => {
      const titleLink = screen.getByRole('link', { name: mockJob.title });
      titleLink.focus();
      await user.keyboard('{Enter}');
      expect(handleClick).toHaveBeenCalledTimes(1);
    },
  },
];

describe('JobCard', () => {
  it.each(basicScenarios)('$name', async ({ verify }) => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<JobCard job={mockJob} isSelected={false} onClick={handleClick} />);
    await verify(user, handleClick);
  });

  it('shows selected state styling when isSelected is true', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={true} onClick={vi.fn()} />);

    // Assert
    const card = screen.getByRole('article', { name: `${mockJob.title} at ${mockJob.company}` });
    expect(card.className).toContain('border-accent');
    expect(screen.getByRole('link', { name: mockJob.title })).toHaveAttribute(
      'aria-expanded',
      'true'
    );
  });

  it('shows unselected state styling when isSelected is false', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    const card = screen.getByRole('article', { name: `${mockJob.title} at ${mockJob.company}` });
    expect(card.className).toContain('border-border');
    expect(screen.getByRole('link', { name: mockJob.title })).toHaveAttribute(
      'aria-expanded',
      'false'
    );
  });

  it('displays match percentage when provided', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} matchPercentage={85.5} />);

    // Assert
    expect(screen.getByText('86% match')).toBeDefined();
  });

  it('does not display match percentage when not provided', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    const percentageElements = screen.queryAllByText(/%/);
    expect(percentageElements).toHaveLength(0);
  });

  it.each(['Software Engineering', 'Internship', 'Hybrid'])(
    'renders the %s badge when available',
    (badgeLabel) => {
      render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);
      expect(screen.getByText(badgeLabel)).toBeDefined();
    }
  );

  it('handles job without optional fields', () => {
    // Arrange
    const minimalJob: JobSummary = {
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

  it('uses a native link so details can be opened in a new tab', () => {
    // Arrange
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    const link = screen.getByRole('link', { name: mockJob.title });
    expect(link).toHaveAttribute('href', `/jobs/${mockJob.id}`);
  });

  it('shows New badge when posted within 24 hours', () => {
    // Arrange
    const recentDate = new Date(Date.now() - 2 * 60 * 60 * 1000); // 2 hours ago
    const recentJob: JobSummary = {
      ...mockJob,
      posted_at: recentDate.toISOString(),
    };

    // Act
    render(<JobCard job={recentJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    expect(screen.getByText('New')).toBeDefined();
  });

  it('does not show New badge for jobs older than 24 hours', () => {
    // Arrange - mockJob.posted_at is from 2024
    render(<JobCard job={mockJob} isSelected={false} onClick={vi.fn()} />);

    // Assert
    expect(screen.queryByText('New')).toBeNull();
  });
});
