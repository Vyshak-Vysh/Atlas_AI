import { describe, expect, it } from "vitest";

import { PRIMARY_NAV, SETTINGS_NAV, projectNav, spaceNav } from "./nav";

// The navigation is the app's information architecture in code. These tests
// pin the properties that break silently: a duplicate href sends two menu
// items to the same screen, and an id that is not interpolated produces a
// link to a literal ":projectId" route that 404s only when clicked.

const isSafeHref = (href: string) => href.startsWith("/") && !href.includes("undefined") && !href.includes(":");

describe("primary navigation", () => {
  it("has unique, absolute hrefs", () => {
    const hrefs = PRIMARY_NAV.map((item) => item.href);
    expect(new Set(hrefs).size, "duplicate href in PRIMARY_NAV").toBe(hrefs.length);
    for (const href of hrefs) {
      expect(isSafeHref(href), `${href} is not a safe absolute path`).toBe(true);
    }
  });

  it("gives every item a label and an icon", () => {
    for (const item of PRIMARY_NAV) {
      expect(item.label).toBeTruthy();
      expect(item.icon).toBeDefined();
    }
  });

  it("keeps settings out of the primary list so it renders separately", () => {
    expect(PRIMARY_NAV.some((item) => item.href === SETTINGS_NAV.href)).toBe(false);
    expect(SETTINGS_NAV.href).toBe("/app/settings");
  });
});

describe("space navigation", () => {
  const spaceId = "3c6b1e55-eb67-4578-94d2-1ebc2c53dfce";
  const items = spaceNav(spaceId);

  it("interpolates the space id into every href", () => {
    expect(items.length).toBeGreaterThan(0);
    for (const item of items) {
      expect(item.href).toContain(spaceId);
      expect(isSafeHref(item.href), `${item.href} looks uninterpolated`).toBe(true);
    }
  });

  it("produces unique hrefs", () => {
    const hrefs = items.map((item) => item.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("does not leak one space's id into another's links", () => {
    const other = spaceNav("11111111-1111-1111-1111-111111111111");
    for (const item of other) {
      expect(item.href).not.toContain(spaceId);
    }
  });
});

describe("project navigation", () => {
  const projectId = "6b57ece3-6db1-4b1f-a43c-e4859e1e3d62";
  const items = projectNav(projectId);

  it("interpolates the project id into every href", () => {
    expect(items.length).toBeGreaterThan(0);
    for (const item of items) {
      expect(item.href).toContain(projectId);
      expect(isSafeHref(item.href), `${item.href} looks uninterpolated`).toBe(true);
    }
  });

  it("produces unique, labelled entries", () => {
    const hrefs = items.map((item) => item.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
    for (const item of items) {
      expect(item.label).toBeTruthy();
      expect(item.icon).toBeDefined();
    }
  });

  it("scopes project links under the project route", () => {
    for (const item of items) {
      expect(item.href.startsWith(`/app/projects/${projectId}`)).toBe(true);
    }
  });
});
