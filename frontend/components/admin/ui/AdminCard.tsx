import { ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

interface AdminCardProps {
  readonly children: ReactNode;
  readonly title?: ReactNode;
  readonly extra?: ReactNode;
  readonly className?: string;
}

export function AdminCard({ children, title, extra, className = '' }: AdminCardProps) {
  return (
    <Card className={className}>
      {(title || extra) && (
        <CardHeader className="items-center px-6 py-4">
          {title && <CardTitle className="text-base">{title}</CardTitle>}
          {extra && <div>{extra}</div>}
        </CardHeader>
      )}
      <CardContent className="px-6 py-4">{children}</CardContent>
    </Card>
  );
}
