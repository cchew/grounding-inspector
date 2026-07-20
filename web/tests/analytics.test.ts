import { describe, it, expect, vi, beforeEach } from "vitest";
import { track } from "../src/analytics";

describe("track", () => {
  beforeEach(() => {
    // @ts-expect-error test cleanup
    delete window.umami;
  });

  it("does nothing when window.umami is not loaded (e.g. ad blocker, test env)", () => {
    expect(() => track("fixture_switched", { id: "travel-pds-01" })).not.toThrow();
  });

  it("calls window.umami.track when available", () => {
    const trackFn = vi.fn();
    // @ts-expect-error test setup
    window.umami = { track: trackFn };
    track("fixture_switched", { id: "travel-pds-01" });
    expect(trackFn).toHaveBeenCalledWith("fixture_switched", { id: "travel-pds-01" });
  });
});
