import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '@/components/ui/Input';
import { Search } from 'lucide-react';

// Clean up DOM after each test
afterEach(() => {
  cleanup();
});

describe('Input', () => {
  it('renders input with placeholder', () => {
    // Arrange
    render(<Input placeholder="Enter text" />);

    // Assert
    expect(screen.getByPlaceholderText('Enter text')).toBeDefined();
  });

  it('renders input with label', () => {
    // Arrange
    render(
      <>
        <label htmlFor="test-input">Test Label</label>
        <Input id="test-input" />
      </>
    );

    // Assert
    expect(screen.getByLabelText('Test Label')).toBeDefined();
  });

  it('handles text input correctly', async () => {
    // Arrange
    const user = userEvent.setup();
    render(<Input placeholder="Type here" />);

    // Act
    const input = screen.getByPlaceholderText('Type here');
    await user.type(input, 'Hello World');

    // Assert
    expect(input).toHaveValue('Hello World');
  });

  it('is disabled when disabled prop is true', () => {
    // Arrange
    render(<Input disabled placeholder="Disabled" />);

    // Assert
    expect(screen.getByPlaceholderText('Disabled')).toBeDisabled();
  });

  it('renders with left icon', () => {
    // Arrange
    render(<Input icon={Search} placeholder="Search..." />);

    // Assert
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
    // Icon should be rendered (we can't easily test for SVG presence)
  });

  it('renders with right icon', () => {
    // Arrange
    render(<Input icon={Search} iconPosition="right" placeholder="Search..." />);

    // Assert
    expect(screen.getByPlaceholderText('Search...')).toBeDefined();
  });

  it('displays error message when error prop is provided', () => {
    // Arrange
    render(<Input error="This field is required" />);

    // Assert
    expect(screen.getByText('This field is required')).toBeDefined();
  });

  it('calls onChange when value changes', async () => {
    // Arrange
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Input onChange={handleChange} />);

    // Act
    const input = screen.getByRole('textbox');
    await user.type(input, 'a');

    // Assert
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders with different input types', () => {
    const { rerender } = render(<Input type="text" />);
    expect(screen.getByRole('textbox')).toBeDefined();

    rerender(<Input type="email" />);
    expect(screen.getByRole('textbox')).toBeDefined();

    rerender(<Input type="password" />);
    // Password inputs don't have role="textbox"
    expect(screen.getByDisplayValue('')).toBeDefined();
  });

  it('applies custom className', () => {
    // Arrange
    render(<Input className="custom-input-class" />);

    // Assert
    const input = screen.getByRole('textbox');
    expect(input.className).toContain('custom-input-class');
  });

  it('passes through additional props', () => {
    // Arrange
    render(<Input data-testid="test-input" aria-label="Test input" maxLength={10} />);

    // Assert
    const input = screen.getByRole('textbox');
    expect(input.getAttribute('data-testid')).toBe('test-input');
    expect(input.getAttribute('aria-label')).toBe('Test input');
    expect(input.getAttribute('maxLength')).toBe('10');
  });

  it('renders with default value', () => {
    // Arrange
    render(<Input defaultValue="default text" />);

    // Assert
    expect(screen.getByDisplayValue('default text')).toBeDefined();
  });

  it('renders with value (controlled)', () => {
    // Arrange
    render(<Input value="controlled value" onChange={() => {}} />);

    // Assert
    expect(screen.getByDisplayValue('controlled value')).toBeDefined();
  });

  it('is required when required prop is true', () => {
    // Arrange
    render(<Input required />);

    // Assert
    expect(screen.getByRole('textbox')).toBeRequired();
  });

  it('has correct name attribute', () => {
    // Arrange
    render(<Input name="username" />);

    // Assert
    expect(screen.getByRole('textbox').getAttribute('name')).toBe('username');
  });

  it('focuses on click', async () => {
    // Arrange
    render(<Input placeholder="Focus me" />);

    // Act
    const input = screen.getByPlaceholderText('Focus me');
    input.focus();

    // Assert
    expect(document.activeElement).toBe(input);
  });
});
