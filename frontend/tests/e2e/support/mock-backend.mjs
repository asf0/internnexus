/* global Buffer, URL, process */

import { createServer } from 'node:http';

const port = Number(process.argv[2] || 4010);
const now = '2026-07-14T18:00:00.000Z';

const jobs = [
  {
    id: 'job-frontend-1',
    source: 'greenhouse',
    title: 'Frontend Engineering Intern',
    company: 'Northstar Labs',
    location: 'Denver, CO',
    city: 'Denver',
    state: 'CO',
    country: 'US',
    apply_url: 'https://example.test/jobs/frontend-1',
    description_html: '<p>Build accessible interfaces with a product engineering team.</p>',
    description_truncated: false,
    job_category: 'software_engineering',
    job_type: 'Internship',
    work_mode: 'Hybrid',
    posted_at: now,
    is_active: true,
  },
  {
    id: 'job-data-2',
    source: 'lever',
    title: 'Data Science Intern',
    company: 'Cedar Analytics',
    location: 'Remote, US',
    city: null,
    state: null,
    country: 'US',
    apply_url: 'https://example.test/jobs/data-2',
    description_html: '<p>Work on practical machine learning and data quality projects.</p>',
    description_truncated: false,
    job_category: 'data_science',
    job_type: 'Internship',
    work_mode: 'Remote',
    posted_at: '2026-07-12T18:00:00.000Z',
    is_active: true,
  },
];

const jobSummaries = jobs.map((job) =>
  Object.fromEntries(Object.entries(job).filter(([key]) => !key.startsWith('description_')))
);

const adminJobs = jobs.map((job, index) => ({
  ...job,
  click_count: 42 - index * 17,
  created_at: '2026-07-01T12:00:00.000Z',
}));

const profile = {
  id: 'user-browser-test',
  email: 'alex@example.test',
  name: 'Alex Rivera',
  image: null,
  created_at: '2026-01-10T12:00:00.000Z',
  bio: 'Computer science student focused on accessible product engineering.',
  phone: '555-0100',
  location: 'Denver, CO',
  job_title: 'Computer Science Student',
  company: 'State University',
  industry: 'Technology',
  skills: ['TypeScript', 'React', 'Python'],
  linkedin_url: 'https://www.linkedin.com/in/example',
  portfolio_url: 'https://example.test',
  preferred_locations: ['Denver, CO', 'Remote'],
  has_password: true,
};

function send(response, status, body) {
  const payload = body === undefined ? '' : JSON.stringify(body);
  response.writeHead(status, {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(payload),
  });
  response.end(payload);
}

createServer((request, response) => {
  const url = new URL(request.url || '/', `http://127.0.0.1:${port}`);

  if (url.pathname === '/health') return send(response, 200, { status: 'ok' });
  if (url.pathname === '/jobs') {
    return send(response, 200, {
      items: jobSummaries,
      total: jobSummaries.length,
      page: 1,
      page_size: 20,
    });
  }
  if (url.pathname.startsWith('/jobs/')) {
    const job = jobs.find((candidate) => `/jobs/${candidate.id}` === url.pathname);
    return job ? send(response, 200, job) : send(response, 404, { detail: 'Job not found' });
  }
  if (url.pathname === '/jobs/filters/companies') {
    return send(response, 200, ['Cedar Analytics', 'Northstar Labs']);
  }
  if (url.pathname === '/jobs/filters/categories') {
    return send(response, 200, ['data_science', 'software_engineering']);
  }
  if (url.pathname === '/jobs/filters/locations') {
    return send(response, 200, [
      { value: 'US', label: 'United States', count: 2, type: 'country' },
    ]);
  }
  if (url.pathname === '/users/me/notifications/unread-count') {
    return send(response, 200, { unread_count: 0 });
  }
  if (
    url.pathname === '/users/me/saved-jobs/ids' ||
    url.pathname === '/users/me/applied-jobs/ids'
  ) {
    return send(response, 200, []);
  }
  if (url.pathname === '/users/me/mcp-keys') return send(response, 200, []);
  if (url.pathname === '/users/me') return send(response, 200, profile);
  if (url.pathname === '/admin/jobs') {
    return send(response, 200, {
      items: adminJobs,
      total: adminJobs.length,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
  }

  return send(response, 404, {
    detail: { message: `No browser-test fixture for ${url.pathname}` },
  });
}).listen(port, '127.0.0.1', () => {
  process.stdout.write(`Mock backend listening on http://127.0.0.1:${port}\n`);
});
