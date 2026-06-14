import { describe, it, expect } from "vitest";
import {
  getMatchColor,
  parseApiError,
  generateJobSlug,
  findJobBySlug,
  toSafeHttpUrl,
} from "@/lib/utils";

describe("getMatchColor", () => {
  it("returns green colors for high match (≥80%)", () => {
    const result = getMatchColor(85);
    expect(result).toContain("green");
  });

  it("returns blue colors for good match (60-79%)", () => {
    const result = getMatchColor(70);
    expect(result).toContain("blue");
  });

  it("returns amber colors for fair match (40-59%)", () => {
    const result = getMatchColor(50);
    expect(result).toContain("amber");
  });

  it("returns gray colors for low match (<40%)", () => {
    const result = getMatchColor(30);
    expect(result).toContain("gray");
  });

  it("handles boundary value of 80%", () => {
    const result = getMatchColor(80);
    expect(result).toContain("green");
  });

  it("handles boundary value of 60%", () => {
    const result = getMatchColor(60);
    expect(result).toContain("blue");
  });

  it("handles boundary value of 40%", () => {
    const result = getMatchColor(40);
    expect(result).toContain("amber");
  });

  it("handles 0%", () => {
    const result = getMatchColor(0);
    expect(result).toContain("gray");
  });

  it("handles 100%", () => {
    const result = getMatchColor(100);
    expect(result).toContain("green");
  });
});

describe("parseApiError", () => {
  it("extracts message from error with detail.message", () => {
    const error = { detail: { message: "Something went wrong" } };
    expect(parseApiError(error)).toBe("Something went wrong");
  });

  it("extracts detail string directly", () => {
    const error = { detail: "Error details" };
    expect(parseApiError(error)).toBe("Error details");
  });

  it("extracts message property", () => {
    const error = { message: "Error message" };
    expect(parseApiError(error)).toBe("Error message");
  });

  it("returns default message for unknown error", () => {
    expect(parseApiError(null)).toBe("An error occurred");
    expect(parseApiError(undefined)).toBe("An error occurred");
    expect(parseApiError("string")).toBe("An error occurred");
    expect(parseApiError(123)).toBe("An error occurred");
  });

  it("handles empty object", () => {
    expect(parseApiError({})).toBe("An error occurred");
  });

  it("handles error with empty message", () => {
    const error = { detail: { message: "" } };
    expect(parseApiError(error)).toBe("An error occurred");
  });
});

describe("generateJobSlug", () => {
  it("generates slug from title, company, and id", () => {
    const result = generateJobSlug("Software Engineer", "Google", "12345678-abcd-1234-5678-123456789abc");
    expect(result).toContain("software-engineer");
    expect(result).toContain("at");
    expect(result).toContain("google");
  });

  it("converts to lowercase", () => {
    const result = generateJobSlug("SENIOR DEVELOPER", "TechCorp", "12345678-abcd-1234-5678-123456789abc");
    expect(result).toBe(result.toLowerCase());
  });

  it("replaces spaces with hyphens", () => {
    const result = generateJobSlug("Data Scientist", "Big Company", "12345678-abcd-1234-5678-123456789abc");
    expect(result).not.toContain(" ");
    expect(result).toContain("-");
  });

  it("removes special characters", () => {
    const result = generateJobSlug("C++ Developer", "Company!", "12345678-abcd-1234-5678-123456789abc");
    expect(result).not.toContain("+");
    expect(result).not.toContain("!");
  });

  it("truncates long titles", () => {
    const longTitle = "A".repeat(100);
    const result = generateJobSlug(longTitle, "Company", "12345678-abcd-1234-5678-123456789abc");
    const parts = result.split("-");
    // Title part should be limited
    expect(parts.length).toBeGreaterThan(0);
  });

  it("truncates long company names", () => {
    const longCompany = "B".repeat(100);
    const result = generateJobSlug("Job", longCompany, "12345678-abcd-1234-5678-123456789abc");
    const parts = result.split("-");
    // Company part should be limited
    expect(parts.length).toBeGreaterThan(0);
  });

  it("removes leading/trailing hyphens", () => {
    const result = generateJobSlug("-Job-", "-Company-", "12345678-abcd-1234-5678-123456789abc");
    expect(result.startsWith("-")).toBe(false);
    expect(result.endsWith("-")).toBe(false);
  });

  it("uses first 8 chars of id as suffix", () => {
    const result = generateJobSlug("Job", "Company", "12345678-abcd-1234-5678-123456789abc");
    expect(result).toContain("12345678");
  });
});

describe("findJobBySlug", () => {
  const jobs = [
    { id: "12345678-abcd-1234-5678-123456789abc", title: "Job 1", company: "Co 1" },
    { id: "87654321-dcba-4321-8765-987654321cba", title: "Job 2", company: "Co 2" },
  ];

  it("finds job by slug suffix", () => {
    const slug = "some-slug-12345678";
    const result = findJobBySlug(jobs, slug);
    expect(result?.title).toBe("Job 1");
  });

  it("returns undefined for non-matching slug", () => {
    const slug = "some-slug-99999999";
    const result = findJobBySlug(jobs, slug);
    expect(result).toBeUndefined();
  });

  it("handles empty jobs array", () => {
    const result = findJobBySlug([], "slug-12345678");
    expect(result).toBeUndefined();
  });
});


describe("toSafeHttpUrl", () => {
  it("accepts http and https URLs", () => {
    expect(toSafeHttpUrl("https://example.com/apply")).toBe("https://example.com/apply");
    expect(toSafeHttpUrl("http://example.com/apply")).toBe("http://example.com/apply");
  });

  it("trims valid URLs", () => {
    expect(toSafeHttpUrl("  https://example.com/apply  ")).toBe("https://example.com/apply");
  });

  it("rejects unsafe or malformed URLs", () => {
    expect(toSafeHttpUrl("javascript:alert(1)")).toBeNull();
    expect(toSafeHttpUrl("data:text/html,hi")).toBeNull();
    expect(toSafeHttpUrl("blob:https://example.com/id")).toBeNull();
    expect(toSafeHttpUrl("/relative/path")).toBeNull();
    expect(toSafeHttpUrl("")).toBeNull();
  });
});
