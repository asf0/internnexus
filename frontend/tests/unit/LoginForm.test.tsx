import { describe, it, expect, vi, afterEach } from "bun:test";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginForm } from "@/components/auth/LoginForm";

// Clean up DOM after each test
afterEach(() => {
  cleanup();
});

describe("LoginForm", () => {
  it("renders login form with email and password fields", () => {
    // Arrange
    render(
      <LoginForm
        isLoading={false}
        onSubmit={vi.fn()}
      />
    );

    // Assert
    expect(screen.getByLabelText(/email address/i)).toBeDefined();
    expect(screen.getByLabelText(/password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /sign in with email/i })).toBeDefined();
  });

  it("calls onSubmit with form data when submitted", async () => {
    // Arrange
    const user = userEvent.setup();
    const handleSubmit = vi.fn((e: { preventDefault: () => void }) => e.preventDefault());
    render(
      <LoginForm
        isLoading={false}
        onSubmit={handleSubmit}
      />
    );

    // Act
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole("button", { name: /sign in with email/i });

    await user.type(emailInput, "test@example.com");
    await user.type(passwordInput, "password123");
    await user.click(submitButton);

    // Assert
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  it("disables inputs when isLoading is true", () => {
    // Arrange
    render(
      <LoginForm
        isLoading={true}
        onSubmit={vi.fn()}
      />
    );

    // Assert
    expect(screen.getByLabelText(/email address/i)).toBeDisabled();
    expect(screen.getByLabelText(/password/i)).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("shows loading state when isLoading is true", () => {
    // Arrange
    render(
      <LoginForm
        isLoading={true}
        onSubmit={vi.fn()}
        submitLabel="Sign in with Email"
      />
    );

    // Assert
    expect(screen.getByText(/signing in/i)).toBeDefined();
  });

  it("shows custom submit label", () => {
    // Arrange
    render(
      <LoginForm
        isLoading={false}
        onSubmit={vi.fn()}
        submitLabel="Custom Sign In"
      />
    );

    // Assert
    expect(screen.getByRole("button", { name: /custom sign in/i })).toBeDefined();
  });

  it("auto-focuses first field when autoFocusFirstField is true", () => {
    // Arrange
    render(
      <LoginForm
        isLoading={false}
        onSubmit={vi.fn()}
        autoFocusFirstField={true}
      />
    );

    // Assert
    const emailInput = screen.getByLabelText(/email address/i);
    expect(emailInput.hasAttribute("autofocus") || document.activeElement === emailInput).toBe(true);
  });

  it("renders email input with correct attributes", () => {
    // Arrange
    render(
      <LoginForm
        isLoading={false}
        onSubmit={vi.fn()}
      />
    );

    // Assert
    const emailInput = screen.getByLabelText(/email address/i);
    expect(emailInput.getAttribute("type")).toBe("email");
    expect(emailInput.getAttribute("name")).toBe("email");
    expect(emailInput).toBeRequired();
    expect(emailInput.getAttribute("placeholder")).toBe("you@example.com");
  });

  it("renders password input with correct attributes", () => {
    // Arrange
    render(
      <LoginForm
        isLoading={false}
        onSubmit={vi.fn()}
      />
    );

    // Assert
    const passwordInput = screen.getByLabelText(/password/i);
    expect(passwordInput.getAttribute("type")).toBe("password");
    expect(passwordInput.getAttribute("name")).toBe("password");
    expect(passwordInput).toBeRequired();
    expect(passwordInput.getAttribute("placeholder")).toBe("••••••••");
  });
});
