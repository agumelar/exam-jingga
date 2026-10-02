import React from 'react';

/**
 * M3Badge - Google Material Design 3 Status Badge
 */
const M3Badge = ({
  children,
  variant = 'default', // 'default' | 'primary' | 'success' | 'warning' | 'error'
  size = 'md', // 'sm' | 'md'
  className = ''
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-black uppercase tracking-wider rounded-full select-none';

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-3 py-1 text-xs'
  };

  const variantStyles = {
    default: 'bg-stone-100 dark:bg-stone-800 text-stone-800 dark:text-stone-300 border border-stone-200 dark:border-stone-700',
    primary: 'bg-orange-100 dark:bg-orange-950/60 text-orange-900 dark:text-orange-200 border border-orange-300 dark:border-orange-800',
    success: 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-900 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-800',
    warning: 'bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-800',
    error: 'bg-rose-100 dark:bg-rose-950/60 text-rose-900 dark:text-rose-200 border border-rose-300 dark:border-rose-800'
  };

  return (
    <span className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}>
      {children}
    </span>
  );
};

export default M3Badge;
