import { auth } from '@/auth';
import { NextResponse } from 'next/server';

const isDev = process.env.NODE_ENV !== 'production';
const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

function generateNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes));
}

function buildCsp(nonce: string): string {
  const scriptSrc = [
    "'self'",
    `'nonce-${nonce}'`,
    'https://pagead2.googlesyndication.com',
    'https://googleads.g.doubleclick.net',
  ];
  scriptSrc.push("'unsafe-eval'");

  const connectSrc = ["'self'", 'https://*.asf0.dev'];
  if (isDev) {
    connectSrc.push(backendUrl);
  }

  return [
    "default-src 'self'",
    `script-src ${scriptSrc.join(' ')}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self'",
    `connect-src ${connectSrc.join(' ')}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "object-src 'none'",
  ].join('; ');
}

function applySecurityHeaders(response: NextResponse, nonce: string): NextResponse {
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  response.headers.set('Content-Security-Policy', buildCsp(nonce));

  if (!isDev) {
    response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  }

  return response;
}

/**
 * Auth-based middleware for admin route protection.
 * This runs via next-auth's auth wrapper.
 */
export const middleware = auth((req) => {
  const { nextUrl } = req;
  const isLoggedIn = !!req.auth;
  const nonce = generateNonce();
  const requestHeaders = new Headers(req.headers);
  requestHeaders.set('x-nonce', nonce);

  // Protect /admin/* routes
  if (nextUrl.pathname.startsWith('/admin')) {
    if (!isLoggedIn) {
      const callbackPath = `${nextUrl.pathname}${nextUrl.search}`;
      const loginUrl = new URL('/', nextUrl.origin);
      loginUrl.searchParams.set('auth', 'required');
      loginUrl.searchParams.set('callbackUrl', callbackPath);
      return applySecurityHeaders(NextResponse.redirect(loginUrl), nonce);
    }
  }

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  return applySecurityHeaders(response, nonce);
});

export const proxy = middleware;

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     * - api routes (handled separately)
     */
    '/((?!_next/static|_next/image|favicon.ico|public/|api/).*)',
  ],
};
