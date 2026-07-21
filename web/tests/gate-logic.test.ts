import { describe, it, expect } from "vitest";
import {
  isAllowedEmail,
  parseAllowedEmails,
  signCookieValue,
  verifyCookieValue,
  gateFormHtml,
  COOKIE_NAME,
} from "../netlify/edge-functions/lib/gate-logic";

describe("parseAllowedEmails", () => {
  it("splits, trims, and lowercases a comma-separated list", () => {
    expect(parseAllowedEmails(" Test@Example.com , other@example.org ")).toEqual([
      "test@example.com",
      "other@example.org",
    ]);
  });

  it("returns an empty list for unset or empty input", () => {
    expect(parseAllowedEmails(undefined)).toEqual([]);
    expect(parseAllowedEmails(null)).toEqual([]);
    expect(parseAllowedEmails("")).toEqual([]);
  });
});

describe("isAllowedEmail", () => {
  const allowed = ["test@example.com", "other@example.org"];

  it("matches allowlisted addresses, case-insensitively", () => {
    expect(isAllowedEmail("test@example.com", allowed)).toBe(true);
    expect(isAllowedEmail("Test@Example.com", allowed)).toBe(true);
    expect(isAllowedEmail("other@example.org", allowed)).toBe(true);
    expect(isAllowedEmail("  test@example.com  ", allowed)).toBe(true);
  });

  it("rejects anything else", () => {
    expect(isAllowedEmail("someone@else.com", allowed)).toBe(false);
    expect(isAllowedEmail("", allowed)).toBe(false);
    expect(isAllowedEmail("test@example.com.evil.com", allowed)).toBe(false);
    expect(isAllowedEmail("test@example.com", [])).toBe(false);
  });
});

describe("cookie signing", () => {
  const secret = "test-secret-value";

  it("round-trips: a signed cookie verifies with the same secret", async () => {
    const signed = await signCookieValue(secret);
    const cookieHeader = `${COOKIE_NAME}=${encodeURIComponent(signed)}`;
    expect(await verifyCookieValue(secret, cookieHeader)).toBe(true);
  });

  it("rejects a cookie signed with a different secret", async () => {
    const signed = await signCookieValue(secret);
    const cookieHeader = `${COOKIE_NAME}=${encodeURIComponent(signed)}`;
    expect(await verifyCookieValue("wrong-secret", cookieHeader)).toBe(false);
  });

  it("rejects a tampered cookie value", async () => {
    const signed = await signCookieValue(secret);
    const tampered = signed.replace(/^1/, "0");
    const cookieHeader = `${COOKIE_NAME}=${encodeURIComponent(tampered)}`;
    expect(await verifyCookieValue(secret, cookieHeader)).toBe(false);
  });

  it("rejects a missing cookie header", async () => {
    expect(await verifyCookieValue(secret, null)).toBe(false);
    expect(await verifyCookieValue(secret, "other=value")).toBe(false);
  });

  it("matches the real cookie by name, not a decoy whose name merely ends in the cookie name", async () => {
    const signed = await signCookieValue(secret);
    const cookieHeader = `other_${COOKIE_NAME}=malicious; ${COOKIE_NAME}=${encodeURIComponent(signed)}`;
    expect(await verifyCookieValue(secret, cookieHeader)).toBe(true);
  });

  it("rejects a header containing only a name-collision decoy (no exact cookie-name match)", async () => {
    const signed = await signCookieValue(secret);
    const cookieHeader = `evil${COOKIE_NAME}=${encodeURIComponent(signed)}`;
    expect(await verifyCookieValue(secret, cookieHeader)).toBe(false);
  });
});

describe("gateFormHtml", () => {
  it("never interpolates an email address into the page", () => {
    expect(gateFormHtml(true)).not.toContain("@");
    expect(gateFormHtml(false)).not.toContain("@");
  });

  it("shows generic rejection copy only when rejected", () => {
    expect(gateFormHtml(false)).not.toContain("Access is limited");
    expect(gateFormHtml(true)).toContain("Access is limited");
  });
});
