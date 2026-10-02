import React, { useEffect } from 'react';
import { X } from 'lucide-react';

/**
 * M3BottomSheet - Google Material Design 3 Modal Bottom Sheet
 */
const M3BottomSheet = ({
  isOpen = false,
  onClose,
  title = '',
  children,
  className = ''
}) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      {/* Scrim Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-300 animate-fade-in"
        onClick={onClose}
      />

      {/* Sheet Surface */}
      <div 
        className={`
          relative z-10 w-full max-w-2xl mx-auto bg-white dark:bg-stone-900 rounded-t-[32px] p-6 text-left border-t border-stone-200 dark:border-stone-800 m3-elevation-4 max-h-[85vh] flex flex-col transition-transform duration-300 ease-out
          ${className}
        `}
      >
        {/* Drag Handle */}
        <div className="flex justify-center -mt-2 mb-3">
          <div className="w-12 h-1.5 rounded-full bg-stone-300 dark:bg-stone-700" />
        </div>

        {/* Header */}
        {(title || onClose) && (
          <div className="flex items-center justify-between pb-4 border-b border-stone-100 dark:border-stone-800 mb-4">
            <h3 className="text-base font-black text-stone-900 dark:text-white uppercase tracking-tight">
              {title}
            </h3>
            {onClose && (
              <button 
                onClick={onClose}
                className="p-2 text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 rounded-full hover:bg-stone-100 dark:hover:bg-stone-800 transition"
              >
                <X size={20} />
              </button>
            )}
          </div>
        )}

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-stone-300 dark:scrollbar-thumb-stone-700">
          {children}
        </div>
      </div>
    </div>
  );
};

export default M3BottomSheet;
