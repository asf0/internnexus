import { ImageResponse } from 'next/og';

// A stable, addressable OG image. Unlike a file-convention
// `opengraph-image.tsx`, this is referenced explicitly from metadata and so is
// not dropped when a page (or layout) overrides `openGraph`.
export const OG_IMAGE_PATH = '/og';
export const OG_IMAGE_ALT = 'InternNexus — Search internships and entry-level jobs';
export const OG_IMAGE_SIZE = {
  width: 1200,
  height: 630,
};

export function GET(): ImageResponse {
  return new ImageResponse(
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '80px',
        background: '#0f172a',
        color: '#ffffff',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <div
          style={{
            width: 88,
            height: 88,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 20,
            background: '#2563eb',
            color: '#ffffff',
            fontSize: 48,
            fontWeight: 700,
            letterSpacing: -2,
          }}
        >
          IN
        </div>
        <div style={{ fontSize: 64, fontWeight: 700, letterSpacing: -2 }}>InternNexus</div>
      </div>
      <div style={{ marginTop: 40, fontSize: 40, color: '#cbd5e1', lineHeight: 1.3 }}>
        Search internships and entry-level roles from company career sites.
      </div>
    </div>,
    { ...OG_IMAGE_SIZE }
  );
}
