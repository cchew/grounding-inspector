import { describe, it, expect } from "vitest";
import {
  isAllowedEmail,
  signCookieValue,
  verifyCookieValue,
  gateFormHtml,
  COOKIE_NAME,
} from "../netlify/edge-functions/gate-logic";

describe("isAllowedEmail", () => {
  it("matches the two allowlisted addresses, case-insensitively", () => {
    expect(isAllowedEmail("test.user@gmail.com")).toBe(true);
    expect(isAllowedEmail("test.user@Gmail.com")).toBe(true);
    expect(isAllowedEmail("test.user@example.org")).toBe(true);
    expect(isAllowedEmail("  test.user@gmail.com  ")).toBe(true);
  });

  it("rejects anything else", () => {
    expect(isAllowedEmail("someone@example.com")).toBe(false);
    expect(isAllowedEmail("")).toBe(false);
    expect(isAllowedEmail("test.user@gmail.com.evil.com")).toBe(false);
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
  it("never mentions the allowlisted addresses", () => {
    const html = gateFormHtml(true);
    expect(html).not.toContain("test.user@gmail.com");
    expect(html).not.toContain("example.org");
  });

  it("shows generic rejection copy only when rejected", () => {
    expect(gateFormHtml(false)).not.toContain("Access is limited");
    expect(gateFormHtml(true)).toContain("Access is limited");
  });
});
