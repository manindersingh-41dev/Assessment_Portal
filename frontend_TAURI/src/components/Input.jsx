/** Accessible input, textarea, and select primitive. */

import React, { useId } from 'react';

export const Input = ({
  label,
  error,
  helperText,
  disabled = false,
  type = 'text',
  as = 'input',
  id,
  className = '',
  'aria-describedby': describedBy,
  ...props
}) => {
  const generatedId = useId();
  const inputId = id || generatedId;
  const errorId = error ? `${inputId}-error` : undefined;
  const helperId = helperText ? `${inputId}-description` : undefined;
  const Component = as === 'textarea' || as === 'select' ? as : 'input';
  const linkedDescriptions = [describedBy, helperId, errorId].filter(Boolean).join(' ') || undefined;
  const baseClasses = `block w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500 dark:bg-slate-900 dark:text-slate-100 dark:disabled:bg-slate-800 ${error ? 'border-danger-500 focus:border-danger-500 focus:ring-danger-500/20' : 'border-slate-300 dark:border-slate-700'} ${Component === 'textarea' ? 'min-h-24 resize-y' : ''} ${className}`;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
          {label}
        </label>
      )}
      <Component
        id={inputId}
        {...(Component === 'input' ? { type } : {})}
        className={baseClasses}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={linkedDescriptions}
        {...props}
      />
      {helperText && !error && <p id={helperId} className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">{helperText}</p>}
      {error && <p id={errorId} className="mt-1.5 text-sm text-danger-600 dark:text-danger-400" role="alert">{error}</p>}
    </div>
  );
};

export default Input;
