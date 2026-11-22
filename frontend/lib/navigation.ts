export function isSafeInternalPath(path: string | undefined): path is string {
  if (!path || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) {
    return false;
  }

  try {
    const base = 'https://internnexus.invalid';
    return new URL(path, base).origin === base;
  } catch {
    return false;
  }
}
