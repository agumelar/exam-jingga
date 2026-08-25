import React from 'react';
import { Check } from 'lucide-react';

/**
 * M3RadioCard - Google Material 3 Interactive Option Card for CBT Questions
 * Digunakan untuk opsi A, B, C, D, E pada ujian siswa dengan zona jempol ramah sentuhan.
 */
const M3RadioCard = ({
  optionKey = 'A',
  optionText = '',
  selected = false,
  doubtful = false,
  onClick,
  disabled = false,
  className = ''
}) => {
  return (
    <div
      role="radio"
      aria-checked={selected}
      tabIndex={disabled ? -1 : 0}
      onClick={disabled ? undefined : onClick}
      onKeyDown={(e) => {
        if (!disabled && (e.key === ' ' || e.key === 'Enter')) {
          e.preventDefault();
          onClick && onClick();
        }
      }}
      className={`
        group relative flex items-start gap-4 p-4 lg:p-5 rounded-3xl cursor-pointer select-none transition-all duration-200 text-left
        ${disabled ? 'opacity-50 pointer-events-none' : 'm3-state-layer'}
        ${selected 
          ? doubtful
            ? 'bg-amber-100 dark:bg-amber-950/40 border-2 border-amber-500 shadow-sm'
            : 'bg-orange-50 dark:bg-orange-950/40 border-2 border-orange-600 dark:border-orange-500 shadow-md shadow-orange-500/10'
          : 'bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 hover:border-stone-300 dark:hover:border-stone-700 m3-elevation-1 hover:m3-elevation-2'}
        ${className}
      `}
    >
      {/* Option Key Avatar (A, B, C, D, E) */}
      <div 
        className={`
          flex-shrink-0 w-11 h-11 rounded-2xl font-black text-sm flex items-center justify-center transition-all duration-200
          ${selected
            ? doubtful
              ? 'bg-amber-500 text-white shadow-md'
              : 'bg-orange-600 dark:bg-orange-500 text-white shadow-md shadow-orange-500/30'
            : 'bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 group-hover:bg-stone-200 dark:group-hover:bg-stone-700'}
        `}
      >
        {selected && !doubtful ? (
          <Check size={20} strokeWidth={3} />
        ) : (
          <span>{optionKey}</span>
        )}
      </div>

      {/* Option Content Text */}
      <div className="flex-1 pt-1.5 min-w-0">
        <div 
          className={`
            text-sm lg:text-base leading-relaxed break-words font-medium
            ${selected 
              ? 'text-stone-900 dark:text-white font-semibold' 
              : 'text-stone-800 dark:text-stone-200'}
          `}
          dangerouslySetInnerHTML={{ __html: optionText }}
        />
      </div>

      {/* Subtle selection ring indicator */}
      {selected && (
        <div className="absolute right-4 top-4 hidden sm:block">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${doubtful ? 'bg-amber-200 dark:bg-amber-900 text-amber-900 dark:text-amber-200' : 'bg-orange-200 dark:bg-orange-900/60 text-orange-900 dark:text-orange-200'}`}>
            {doubtful ? 'Ragu' : 'Dipilih'}
          </span>
        </div>
      )}
    </div>
  );
};

export default M3RadioCard;
