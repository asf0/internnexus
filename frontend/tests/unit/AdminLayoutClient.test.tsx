import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/admin/jobs/123",
}));

vi.mock("next-auth/react", () => ({
  signOut: vi.fn(() => Promise.resolve()),
}));

import AdminLayoutClient from "@/app/admin/AdminLayoutClient";

afterEach(() => {
  cleanup();
});

describe("AdminLayoutClient", () => {
  it("renders fixed admin navigation and content for admins", () => {
    render(
      <AdminLayoutClient
        user={{ id: "user-1", name: "Ada Admin", email: "ada@example.com", image: null }}
        isAdmin={true}
      >
        <main>Admin body</main>
      </AdminLayoutClient>
    );

    const navs = screen.getAllByLabelText("Admin navigation");
    expect(navs.length).toBe(2);
    expect(screen.getAllByText("Jobs").length).toBeGreaterThan(0);
    expect(screen.getByText("InternNexus Admin")).toBeDefined();
    expect(screen.getByText("Admin body")).toBeDefined();
    expect(screen.queryByLabelText("Collapse sidebar")).toBeNull();
  });

  it("renders access denied for non-admin users", () => {
    render(
      <AdminLayoutClient user={{ id: "user-1", email: "user@example.com" }} isAdmin={false}>
        <main>Admin body</main>
      </AdminLayoutClient>
    );

    expect(screen.getByText("Access Denied")).toBeDefined();
    expect(screen.queryByText("Admin body")).toBeNull();
  });
});
