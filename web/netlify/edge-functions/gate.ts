// netlify/edge-functions/gate.ts
import type { Context } from "@netlify/edge-functions";
import {
  isAllowedEmail,
  signCookieValue,
  verifyCookieValue,
  gateFormHtml,
  COOKIE_NAME,
  COOKIE_MAX_AGE,
} from "./lib/gate-logic.ts";

export default async (request: Request, context: Context) => {
  const secret = Netlify.env.get("GATE_SECRET");
  if (!secret || secret.length < 16) {
    return new Response("Server misconfigured", { status: 500 });
  }

  if (request.method === "POST") {
    const form = await request.formData();
    const email = String(form.get("email") ?? "");
    if (!isAllowedEmail(email)) {
      return new Response(gateFormHtml(true), {
        status: 401,
        headers: { "content-type": "text/html" },
      });
    }
    const signed = await signCookieValue(secret);
    const headers = new Headers({ location: "/" });
    headers.append(
      "set-cookie",
      `${COOKIE_NAME}=${encodeURIComponent(signed)}; Path=/; Max-Age=${COOKIE_MAX_AGE}; HttpOnly; Secure; SameSite=Lax`,
    );
    return new Response(null, { status: 302, headers });
  }

  const authed = await verifyCookieValue(secret, request.headers.get("cookie"));
  if (authed) {
    return context.next();
  }
  return new Response(gateFormHtml(false), {
    status: 200,
    headers: { "content-type": "text/html" },
  });
};
