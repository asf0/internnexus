export function toSafeJsonLd(data: unknown): string {
  return JSON.stringify(data).replace(/[<>&\u2028\u2029]/g, (char) => {
    switch (char) {
      case '<':
        return String.raw`\u003c`;
      case '>':
        return String.raw`\u003e`;
      case '&':
        return String.raw`\u0026`;
      case '\u2028':
        return String.raw`\u2028`;
      case '\u2029':
        return String.raw`\u2029`;
      default:
        return char;
    }
  });
}
