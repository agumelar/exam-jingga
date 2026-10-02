import React from 'react';
import { X, LayoutGrid, CheckCircle2, HelpCircle, Circle } from 'lucide-react';

const ExamQuestionDrawer = ({
  isOpen,
  onClose,
  questions = [],
  currentIndex = 0,
  onSelectQuestion,
  answers = {},
  doubts = []
}) => {
  if (!isOpen) return null;

  const answeredCount = Object.keys(answers).length;
  const totalCount = questions.length;
  const progressPercent = totalCount > 0 ? Math.round((answeredCount / totalCount) * 100) : 0;

  return (
    <div 
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex flex-col justify-end animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="bg-white dark:bg-zinc-900 w-full max-w-2xl mx-auto rounded-t-[2.5rem] p-6 sm:p-8 shadow-2xl border-t border-slate-100 dark:border-zinc-800 max-h-[85vh] flex flex-col animate-in slide-in-from-bottom duration-300"
        onClick={e => e.stopPropagation()}
      >
        {/* Drawer Handle & Header */}
        <div className="w-12 h-1.5 bg-slate-300 dark:bg-zinc-700 rounded-full mx-auto mb-4"></div>
        
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-orange-100 dark:bg-orange-950/40 text-orange-600 rounded-xl">
              <LayoutGrid size={18} />
            </div>
            <div>
              <h3 className="text-base font-black uppercase italic tracking-tight text-slate-900 dark:text-white">
                Daftar Nomor Soal
              </h3>
              <p className="text-[10px] font-bold text-slate-400 dark:text-zinc-500 uppercase tracking-widest">
                Terjawab: {answeredCount} dari {totalCount} ({progressPercent}%)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Tutup Drawer"
            className="p-2.5 rounded-xl bg-slate-100 dark:bg-zinc-800 text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden mb-6">
          <div 
            className="bg-gradient-to-r from-orange-500 to-orange-600 h-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          ></div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center justify-around gap-2 mb-6 p-3 rounded-2xl bg-slate-50 dark:bg-zinc-950/60 border border-slate-100 dark:border-zinc-800/80 text-[10px] font-black uppercase">
          <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
            <div className="w-3 h-3 bg-emerald-500 rounded-md"></div>
            <span>Sudah Dijawab</span>
          </div>
          <div className="flex items-center gap-1.5 text-amber-500">
            <div className="w-3 h-3 bg-amber-400 rounded-md"></div>
            <span>Ragu-Ragu</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-400 dark:text-zinc-500">
            <div className="w-3 h-3 bg-slate-200 dark:bg-zinc-800 rounded-md"></div>
            <span>Belum</span>
          </div>
        </div>

        {/* Question Numbers Grid (5 or 6 columns) */}
        <div className="flex-1 overflow-y-auto pr-1 py-1 grid grid-cols-5 sm:grid-cols-6 gap-2.5 max-h-[45vh] custom-scrollbar">
          {questions.map((q, idx) => {
            const qIdStr = String(q.id);
            const isAnswered = !!answers[qIdStr];
            const isDoubt = doubts.includes(qIdStr);
            const isCurrent = currentIndex === idx;

            let btnStyle = 'bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400';
            if (isDoubt) {
              btnStyle = 'bg-amber-400 text-slate-950 font-black shadow-md shadow-amber-400/20';
            } else if (isAnswered) {
              btnStyle = 'bg-emerald-500 text-white font-black shadow-md shadow-emerald-500/20';
            }

            return (
              <button
                key={q.id}
                onClick={() => {
                  onSelectQuestion(idx);
                  onClose();
                }}
                className={`h-12 rounded-2xl text-xs font-black transition-all flex flex-col items-center justify-center relative cursor-pointer active:scale-95 ${btnStyle} ${
                  isCurrent ? 'ring-3 ring-orange-600 ring-offset-2 dark:ring-offset-zinc-900 scale-105 shadow-xl z-10' : ''
                }`}
              >
                <span>{idx + 1}</span>
                {isAnswered && (
                  <span className="text-[8px] opacity-80 uppercase leading-none font-bold">
                    {answers[qIdStr]}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Footer Button */}
        <button
          onClick={onClose}
          className="mt-6 w-full py-4 bg-orange-600 hover:bg-orange-700 text-white rounded-2xl font-black uppercase text-xs tracking-widest transition-all shadow-lg shadow-orange-600/20 cursor-pointer"
        >
          Lanjut Mengerjakan Soal {currentIndex + 1}
        </button>
      </div>
    </div>
  );
};

export default ExamQuestionDrawer;
