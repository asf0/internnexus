export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'green';
    case 'running':
      return 'blue';
    case 'failed':
      return 'red';
    default:
      return 'default';
  }
}
