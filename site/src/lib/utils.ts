import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function complexityBadgeClass(level?: string | null): string {
  switch ((level || '').toUpperCase()) {
    case 'L1': return 'badge badge-l1';
    case 'L2': return 'badge badge-l2';
    case 'L3': return 'badge badge-l3';
    default:   return 'badge badge-l1';
  }
}
