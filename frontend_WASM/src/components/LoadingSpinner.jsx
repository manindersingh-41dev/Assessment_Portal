/** Loading indicator with a screen-reader status label. */

import React from 'react';
import { LoaderCircle } from 'lucide-react';

const sizeClasses = {
  xs: 'h-3.5 w-3.5',
  sm: 'h-4 w-4',
  md: 'h-7 w-7',
  lg: 'h-10 w-10',
};

export const LoadingSpinner = ({ size = 'md', fullScreen = false, label = 'Loading' }) => {
  const content = (
    <div className="flex items-center justify-center gap-3" role="status" aria-live="polite">
      <LoaderCircle className={`${sizeClasses[size] || sizeClasses.md} animate-spin text-primary-600 dark:text-primary-400`} aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </div>
  );

  if (fullScreen) {
    return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/10 dark:bg-black/30">{content}</div>;
  }
  return content;
};

export default LoadingSpinner;
