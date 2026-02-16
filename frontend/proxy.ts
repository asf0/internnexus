import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function proxy(request: NextRequest) {
  if (request.nextUrl.pathname === "/api/auth/session") {
    return new NextResponse(null, { status: 404 })
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: "/api/auth/session",
}
