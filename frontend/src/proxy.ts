import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Auth is handled client-side in (app)/layout.tsx via useAuth().
// Middleware only passes all requests through — no server-side redirects.
export function proxy(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
