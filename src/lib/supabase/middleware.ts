import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
  // Internal research tool — no auth needed.
  // Just pass through all requests without Supabase session management.
  return NextResponse.next({ request })
}
