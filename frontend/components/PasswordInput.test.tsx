/// <reference lib="dom" />

import { describe, test, expect, mock, beforeEach } from 'bun:test';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import React from 'react';

// Dynamic import for the component after mocks
let PasswordInput: typeof import('./PasswordInput').default;
let calculateStrength: typeof import('./PasswordInput').calculateStrength;
let SPECIAL_CHARS: typeof import('./PasswordInput').SPECIAL_CHARS;

describe('PasswordInput Component', () => {
  const mockOnChange = mock();
  const mockOnConfirmChange = mock();

  beforeEach(async () => {
    mockOnChange.mockClear();
    mockOnConfirmChange.mockClear();
    const module = await import('./PasswordInput');
    PasswordInput = module.default;
    calculateStrength = module.calculateStrength;
    SPECIAL_CHARS = module.SPECIAL_CHARS;
  });

  describe('Rendering', () => {
    test('renders password input with label', () => {
      render(React.createElement(PasswordInput, { value: '', onChange: mockOnChange }));
      
      expect(screen.getByLabelText('Password')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    });

    test('renders with custom label', () => {
      render(React.createElement(PasswordInput, { value: '', onChange: mockOnChange, label: 'New Password' }));
      
      expect(screen.getByLabelText('New Password')).toBeInTheDocument();
    });

    test('renders confirm password when showConfirmation is true', () => {
      render(
        React.createElement(PasswordInput, {
          value: '',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: '',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument();
    });

    test('renders custom confirm password label', () => {
      render(
        React.createElement(PasswordInput, {
          value: '',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: '',
          onConfirmChange: mockOnConfirmChange,
          confirmLabel: 'Verify Password'
        })
      );
      
      expect(screen.getByLabelText('Verify Password')).toBeInTheDocument();
    });
  });

  describe('Password Visibility Toggle', () => {
    test('toggles password visibility', () => {
      render(React.createElement(PasswordInput, { value: 'password123', onChange: mockOnChange }));
      
      const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;
      const toggleButton = screen.getAllByRole('button')[0];
      
      // Initially hidden
      expect(passwordInput).toHaveAttribute('type', 'password');
      
      // Click to show
      fireEvent.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'text');
      
      // Click to hide again
      fireEvent.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('toggles confirm password visibility separately', () => {
      render(
        React.createElement(PasswordInput, {
          value: 'password123',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: 'password123',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;
      const confirmInput = screen.getByLabelText('Confirm Password') as HTMLInputElement;
      const toggleButtons = screen.getAllByRole('button');
      
      // Toggle confirm password only
      fireEvent.click(toggleButtons[1]);
      
      expect(passwordInput).toHaveAttribute('type', 'password');
      expect(confirmInput).toHaveAttribute('type', 'text');
    });
  });

  describe('Password Input Change', () => {
    test('calls onChange when password is typed', () => {
      render(React.createElement(PasswordInput, { value: '', onChange: mockOnChange }));
      
      const passwordInput = screen.getByLabelText('Password');
      fireEvent.change(passwordInput, { target: { value: 'newpassword' } });
      
      expect(mockOnChange).toHaveBeenCalledWith('newpassword');
    });

    test('calls onConfirmChange when confirm password is typed', () => {
      render(
        React.createElement(PasswordInput, {
          value: 'password123',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: '',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      const confirmInput = screen.getByLabelText('Confirm Password');
      fireEvent.change(confirmInput, { target: { value: 'password123' } });
      
      expect(mockOnConfirmChange).toHaveBeenCalledWith('password123');
    });
  });

  describe('Strength Indicator', () => {
    test('displays strength indicator when password has value', () => {
      render(React.createElement(PasswordInput, { value: 'password', onChange: mockOnChange }));
      
      expect(screen.getByText('Password strength')).toBeInTheDocument();
    });

    test('does not display strength indicator when password is empty', () => {
      render(React.createElement(PasswordInput, { value: '', onChange: mockOnChange }));
      
      expect(screen.queryByText('Password strength')).not.toBeInTheDocument();
    });

    test('hides strength indicator when showStrengthIndicator is false', () => {
      render(React.createElement(PasswordInput, { value: 'password', onChange: mockOnChange, showStrengthIndicator: false }));
      
      expect(screen.queryByText('Password strength')).not.toBeInTheDocument();
    });

    test('displays correct strength level', () => {
      const { rerender } = render(React.createElement(PasswordInput, { value: 'weak', onChange: mockOnChange }));
      expect(screen.getByText('weak')).toBeInTheDocument();
      
      // Weak1! has 4/5 requirements (length, uppercase, lowercase, special) but no number = 80% = good
      rerender(React.createElement(PasswordInput, { value: 'Weak1!', onChange: mockOnChange }));
      expect(screen.getByText('good')).toBeInTheDocument();
      
      rerender(React.createElement(PasswordInput, { value: 'StrongPass1!', onChange: mockOnChange }));
      expect(screen.getByText('strong')).toBeInTheDocument();
    });
  });

  describe('Requirements Checklist', () => {
    test('displays all requirements', () => {
      render(React.createElement(PasswordInput, { value: '', onChange: mockOnChange }));
      
      expect(screen.getByText('8+ characters')).toBeInTheDocument();
      expect(screen.getByText('1 uppercase letter')).toBeInTheDocument();
      expect(screen.getByText('1 lowercase letter')).toBeInTheDocument();
      expect(screen.getByText('1 number')).toBeInTheDocument();
      expect(screen.getByText('1 special character')).toBeInTheDocument();
    });

    test('marks requirements as met', () => {
      render(React.createElement(PasswordInput, { value: 'Pass1!', onChange: mockOnChange }));
      
      const metRequirements = screen.getAllByText(/characters|uppercase|lowercase|number|special/)
        .filter(el => el.classList.contains('text-green-600') || el.classList.contains('text-green-400'));
      
      expect(metRequirements.length).toBeGreaterThan(0);
    });

    test('hides requirements when showRequirements is false', () => {
      render(React.createElement(PasswordInput, { value: '', onChange: mockOnChange, showRequirements: false }));
      
      expect(screen.queryByText('8+ characters')).not.toBeInTheDocument();
    });
  });

  describe('Password Confirmation Validation', () => {
    test('shows error when passwords do not match', () => {
      render(
        React.createElement(PasswordInput, {
          value: 'password123',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: 'different',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
    });

    test('does not show error when passwords match', () => {
      render(
        React.createElement(PasswordInput, {
          value: 'password123',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: 'password123',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      expect(screen.queryByText('Passwords do not match')).not.toBeInTheDocument();
    });

    test('does not show error when confirm password is empty', () => {
      render(
        React.createElement(PasswordInput, {
          value: 'password123',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: '',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      expect(screen.queryByText('Passwords do not match')).not.toBeInTheDocument();
    });

    test('applies error styling to confirm input when passwords do not match', () => {
      render(
        React.createElement(PasswordInput, {
          value: 'password123',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: 'different',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      const confirmInput = screen.getByLabelText('Confirm Password');
      expect(confirmInput).toHaveClass('border-red-300');
    });
  });

  describe('Disabled State', () => {
    test('disables inputs when disabled prop is true', () => {
      render(React.createElement(PasswordInput, { value: 'password', onChange: mockOnChange, disabled: true }));
      
      const passwordInput = screen.getByLabelText('Password');
      expect(passwordInput).toBeDisabled();
    });

    test('disables confirm input when disabled prop is true', () => {
      render(
        React.createElement(PasswordInput, {
          value: 'password123',
          onChange: mockOnChange,
          showConfirmation: true,
          confirmValue: 'password123',
          onConfirmChange: mockOnConfirmChange,
          disabled: true
        })
      );
      
      const confirmInput = screen.getByLabelText('Confirm Password');
      expect(confirmInput).toBeDisabled();
    });
  });

  describe('Custom ID', () => {
    test('uses custom id for password input', () => {
      render(React.createElement(PasswordInput, { value: '', onChange: mockOnChange, id: 'custom-password' }));
      
      const passwordInput = screen.getByLabelText('Password');
      expect(passwordInput).toHaveAttribute('id', 'custom-password');
    });

    test('generates confirm id based on custom id', () => {
      render(
        React.createElement(PasswordInput, {
          value: '',
          onChange: mockOnChange,
          id: 'custom-password',
          showConfirmation: true,
          confirmValue: '',
          onConfirmChange: mockOnConfirmChange
        })
      );
      
      const confirmInput = screen.getByLabelText('Confirm Password');
      expect(confirmInput).toHaveAttribute('id', 'custom-password-confirm');
    });
  });
});

describe('calculateStrength function', () => {
  test('returns weak for short password', () => {
    const result = calculateStrength('short');
    expect(result.level).toBe('weak');
    expect(result.score).toBeLessThan(40);
  });

  test('returns good for password without uppercase', () => {
    // password123! has 4/5 requirements: length, lowercase, number, special
    const result = calculateStrength('password123!');
    expect(result.level).toBe('good');
  });

  test('returns good for password without lowercase', () => {
    // PASSWORD123! has 4/5 requirements: length, uppercase, number, special
    const result = calculateStrength('PASSWORD123!');
    expect(result.level).toBe('good');
  });

  test('returns good for password without number', () => {
    // Password! has 4/5 requirements: length, uppercase, lowercase, special
    const result = calculateStrength('Password!');
    expect(result.level).toBe('good');
  });

  test('returns good for password without special character', () => {
    // Password123 has 4/5 requirements: length, uppercase, lowercase, number
    const result = calculateStrength('Password123');
    expect(result.level).toBe('good');
  });

  test('returns good for partially strong password', () => {
    // Password1 has 4/5 requirements: length, uppercase, lowercase, number
    const result = calculateStrength('Password1');
    expect(result.level).toBe('good');
  });

  test('returns good for mostly strong password', () => {
    // Password12 has 4/5 requirements: length, uppercase, lowercase, number
    const result = calculateStrength('Password12');
    expect(result.level).toBe('good');
  });

  test('returns strong for fully compliant password', () => {
    const result = calculateStrength('Password123!');
    expect(result.level).toBe('strong');
    expect(result.score).toBe(100);
  });

  test('returns all requirements', () => {
    const result = calculateStrength('Pass1!');
    expect(result.requirements).toHaveLength(5);
    expect(result.requirements[0].label).toBe('8+ characters');
    expect(result.requirements[1].label).toBe('1 uppercase letter');
    expect(result.requirements[2].label).toBe('1 lowercase letter');
    expect(result.requirements[3].label).toBe('1 number');
    expect(result.requirements[4].label).toBe('1 special character');
  });

  test('correctly identifies met requirements', () => {
    const result = calculateStrength('Password1!');
    
    expect(result.requirements[0].met).toBe(true); // 8+ chars
    expect(result.requirements[1].met).toBe(true); // uppercase
    expect(result.requirements[2].met).toBe(true); // lowercase
    expect(result.requirements[3].met).toBe(true); // number
    expect(result.requirements[4].met).toBe(true); // special char
  });

  test('correctly identifies unmet requirements', () => {
    const result = calculateStrength('pass');
    
    expect(result.requirements[0].met).toBe(false); // 8+ chars
    expect(result.requirements[1].met).toBe(false); // uppercase
    expect(result.requirements[2].met).toBe(true);  // lowercase
    expect(result.requirements[3].met).toBe(false); // number
    expect(result.requirements[4].met).toBe(false); // special char
  });
});

describe('SPECIAL_CHARS constant', () => {
  test('contains expected special characters', () => {
    expect(SPECIAL_CHARS).toContain('!');
    expect(SPECIAL_CHARS).toContain('@');
    expect(SPECIAL_CHARS).toContain('#');
    expect(SPECIAL_CHARS).toContain('$');
    expect(SPECIAL_CHARS).toContain('%');
    expect(SPECIAL_CHARS).toContain('^');
    expect(SPECIAL_CHARS).toContain('&');
    expect(SPECIAL_CHARS).toContain('*');
  });
});
