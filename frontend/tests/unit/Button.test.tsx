import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/Button";

// Clean up DOM after each test
afterEach(() => {
  cleanup();
});

describe("Button", () => {
  it("renders button with text", () => {
    // Arrange
    render(<Button>Click me</Button>);

    // Assert
    expect(screen.getByRole("button", { name: "Click me" })).toBeDefined();
  });

  it("renders with different variants", () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>);
    expect(screen.getByRole("button")).toBeDefined();

    rerender(<Button variant="secondary">Secondary</Button>);
    expect(screen.getByRole("button")).toBeDefined();

    rerender(<Button variant="outline">Outline</Button>);
    expect(screen.getByRole("button")).toBeDefined();

    rerender(<Button variant="ghost">Ghost</Button>);
    expect(screen.getByRole("button")).toBeDefined();
  });

  it("renders with different sizes", () => {
    const { rerender } = render(<Button size="sm">Small</Button>);
    expect(screen.getByRole("button")).toBeDefined();

    rerender(<Button size="md">Medium</Button>);
    expect(screen.getByRole("button")).toBeDefined();

    rerender(<Button size="lg">Large</Button>);
    expect(screen.getByRole("button")).toBeDefined();
  });

  it("calls onClick when clicked", async () => {
    // Arrange
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    // Act
    await user.click(screen.getByRole("button"));

    // Assert
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when disabled prop is true", () => {
    // Arrange
    render(<Button disabled>Disabled</Button>);

    // Assert
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("does not call onClick when disabled", async () => {
    // Arrange
    const user = userEvent.setup();
    const handleClick = vi.fn();
    render(
      <Button disabled onClick={handleClick}>
        Disabled
      </Button>
    );

    // Act
    await user.click(screen.getByRole("button"));

    // Assert
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("renders as different element with asChild", () => {
    // Arrange
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    );

    // Assert
    expect(screen.getByRole("link", { name: "Link Button" })).toBeDefined();
  });

  it("applies custom className", () => {
    // Arrange
    render(<Button className="custom-class">Custom</Button>);

    // Assert
    const button = screen.getByRole("button");
    expect(button.className).toContain("custom-class");
  });

  it("renders with type attribute", () => {
    // Arrange
    const { rerender } = render(<Button type="button">Button</Button>);
    expect(screen.getByRole("button").getAttribute("type")).toBe("button");

    rerender(<Button type="submit">Submit</Button>);
    expect(screen.getByRole("button").getAttribute("type")).toBe("submit");

    rerender(<Button type="reset">Reset</Button>);
    expect(screen.getByRole("button").getAttribute("type")).toBe("reset");
  });

  it("passes through additional props", () => {
    // Arrange
    render(
      <Button data-testid="test-button" aria-label="Test button">
        Test
      </Button>
    );

    // Assert
    const button = screen.getByRole("button");
    expect(button.getAttribute("data-testid")).toBe("test-button");
    expect(button.getAttribute("aria-label")).toBe("Test button");
  });
});
