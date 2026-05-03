import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = new Set(["/", "/login", "/signup"]);

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths unconditionally
  if (PUBLIC_PATHS.has(pathname)) {
    return NextResponse.next();
  }

  // Soft check: presence of session cookie set on login
  const sessionCookie = request.cookies.get("autods_session");

  if (!sessionCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Run on all routes except static assets and Next.js internals
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
