import { describe, it, expect, vi, beforeEach } from "vitest";

const driveMock = vi.fn();
let lastConfig: any;
vi.mock("driver.js", () => ({
  driver: vi.fn((config: any) => {
    lastConfig = config;
    return { drive: driveMock, destroy: vi.fn() };
  }),
}));

import { startTour, hasSeenTour, TOUR_SEEN_KEY } from "../src/tour";

describe("tour", () => {
  beforeEach(() => {
    localStorage.clear();
    driveMock.mockClear();
  });

  it("hasSeenTour is false until the flag is set", () => {
    expect(hasSeenTour()).toBe(false);
    localStorage.setItem(TOUR_SEEN_KEY, "1");
    expect(hasSeenTour()).toBe(true);
  });

  it("starts and drives the tour", () => {
    startTour();
    expect(driveMock).toHaveBeenCalled();
  });

  it("targets the four key first-visit elements in order", () => {
    startTour();
    const targets = lastConfig.steps.map((s: any) => s.element);
    expect(targets).toEqual([
      ".fixture-nav",
      ".pane-claims",
      ".pane-source",
      ".help-btn",
    ]);
  });
});
