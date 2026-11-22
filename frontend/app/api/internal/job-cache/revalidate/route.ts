import { timingSafeEqual } from 'node:crypto';

import { revalidateTag } from 'next/cache';
import { NextResponse } from 'next/server';
import { z } from 'zod';

const MAX_JOB_IDS = 100;
const RevalidationRequestSchema = z.object({
  job_ids: z.array(z.string().uuid()).min(1).max(MAX_JOB_IDS),
});

function hasValidAuthorization(request: Request): boolean {
  const secret = process.env.JOB_CACHE_REVALIDATION_SECRET;
  const authorization = request.headers.get('authorization');
  if (!secret || !authorization?.startsWith('Bearer ')) return false;

  const token = authorization.slice('Bearer '.length);
  const expected = Buffer.from(secret);
  const received = Buffer.from(token);
  return expected.length === received.length && timingSafeEqual(expected, received);
}

export async function POST(request: Request): Promise<NextResponse> {
  if (!hasValidAuthorization(request)) {
    return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
  }

  const parsed = RevalidationRequestSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ detail: 'Invalid job_ids' }, { status: 400 });
  }

  for (const jobId of new Set(parsed.data.job_ids)) {
    revalidateTag(`job:${jobId}`, 'max');
  }
  return NextResponse.json({ revalidated: parsed.data.job_ids.length });
}
