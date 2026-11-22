import { ReactNode } from 'react';

interface LegalSectionProps {
  readonly title: string;
  readonly children: ReactNode;
}

export default function LegalSection({ title, children }: LegalSectionProps) {
  return (
    <section className="border-border border-t pt-6 first:border-0 first:pt-0">
      <h3 className="text-foreground text-base font-semibold">{title}</h3>
      <div className="text-foreground-secondary mt-2 space-y-3 text-sm leading-6">{children}</div>
    </section>
  );
}
