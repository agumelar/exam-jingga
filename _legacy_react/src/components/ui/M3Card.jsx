import React from 'react';

/**
 * M3Card - Google Material Design 3 Surface Card Component
 * Variants: 'elevated' | 'filled' | 'outlined'
 */
const M3Card = ({
  children,
  variant = 'elevated',
  interactive = false,
  className = '',
  onClick,
  ...props
}) => {
  const baseStyles = 'rounded-3xl transition-all duration-200 text-left';

  const variantStyles = {
    elevated: 'bg-white dark:bg-stone-900 border border-stone-200/60 dark:border-stone-800 m3-elevation-1 hover:m3-elevation-2',
    filled: 'bg-stone-100 dark:bg-stone-800/70 border-none',
    outlined: 'bg-transparent border border-stone-300 dark:border-stone-700'
  };

  const interactiveStyles = interactive 
    ? 'm3-state-layer cursor-pointer hover:border-orange-500/50 hover:shadow-md active:scale-[0.99]' 
    : '';

  return (
    <div
      onClick={onClick}
      className={`
        ${baseStyles}
        ${variantStyles[variant] || variantStyles.elevated}
        ${interactiveStyles}
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  );
};

export default M3Card;
