import React, { useRef, useEffect } from 'react';
import { KeyRound, X, Sparkles, ClipboardPaste } from 'lucide-react';

const TokenInputOTP = ({
  isOpen,
  onClose,
  onSubmit,
  loading = false,
  examTitle = '',
  examType = ''
}) => {
  const [digits, setDigits] = React.useState(['', '', '', '', '', '']);
  const inputRefs = useRef([]);

  useEffect(() => {
    if (isOpen) {
      setDigits(['', '', '', '', '', '']);
      setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 100);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleChange = (index, value) => {
    const cleanVal = value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    
    // Jika paste multi-karakter
    if (cleanVal.length > 1) {
      const chars = cleanVal.slice(0, 6).split('');
      const newDigits = [...digits];
      chars.forEach((ch, i) => {
        if (index + i < 6) newDigits[index + i] = ch;
      });
      setDigits(newDigits);
      const nextIndex = Math.min(index + chars.length, 5);
      inputRefs.current[nextIndex]?.focus();
      return;
    }

    const newDigits = [...digits];
    newDigits[index] = cleanVal;
    setDigits(newDigits);

    if (cleanVal && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (!pasted) return;
    const chars = pasted.slice(0, 6).split('');
    const newDigits = ['', '', '', '', '', ''];
    chars.forEach((c, idx) => {
      newDigits[idx] = c;
    });
    setDigits(newDigits);
    const focusIndex = Math.min(chars.length, 5);
    inputRefs.current[focusIndex]?.focus();
  };

  const tokenString = digits.join('');

  const handleSubmit = () => {
    if (tokenString.length !== 6) return;
    onSubmit(tokenString);
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="bg-white dark:bg-zinc-950 w-full max-w-md rounded-[3rem] p-8 sm:p-10 shadow-2xl relative border border-slate-100 dark:border-zinc-800 animate-in zoom-in-95 duration-200"
        onClick={e => e.stopPropagation()}
      >
        <button 
          onClick={onClose}
          aria-label="Tutup Modal"
          className="absolute top-6 right-6 p-3 text-slate-400 hover:text-slate-900 dark:hover:text-white rounded-2xl hover:bg-slate-100 dark:hover:bg-zinc-900 transition-colors"
        >
          <X size={20}/>
        </button>

        <div className="text-center mb-6">
          <div className="inline-flex p-4 bg-orange-100 dark:bg-orange-950/40 text-orange-600 rounded-3xl mb-4 shadow-lg shadow-orange-600/10">
            <KeyRound size={36} />
          </div>
          
          <div className="flex items-center justify-center gap-2 mb-1">
            <span className="bg-orange-600 text-white px-2.5 py-0.5 rounded-lg text-[9px] font-black uppercase tracking-wider">
              {examType || 'UJIAN'}
            </span>
            <h3 className="text-xl font-black uppercase italic tracking-tight text-slate-900 dark:text-white">
              Verifikasi Token
            </h3>
          </div>
          <p className="text-xs font-bold text-slate-500 dark:text-zinc-400 truncate max-w-xs mx-auto">
            {examTitle}
          </p>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-2">
            Minta 6 digit token (huruf/angka) kepada pengawas
          </p>
        </div>

        {/* 6-box OTP input */}
        <div 
          onPaste={handlePaste}
          className="flex justify-center gap-2 sm:gap-3 mb-8"
        >
          {digits.map((digit, index) => (
            <input
              key={index}
              ref={el => inputRefs.current[index] = el}
              type="text"
              inputMode="text"
              autoCapitalize="characters"
              autoComplete="one-time-code"
              maxLength={1}
              value={digit}
              onChange={e => handleChange(index, e.target.value)}
              onKeyDown={e => handleKeyDown(index, e)}
              className={`w-11 sm:w-12 h-16 bg-slate-50 dark:bg-zinc-900 border-2 rounded-2xl text-center text-2xl font-black font-mono transition-all outline-none ${
                digit 
                  ? 'border-orange-500 text-orange-600 dark:text-orange-400 bg-orange-50/50 dark:bg-orange-950/20 shadow-md shadow-orange-500/10 scale-105' 
                  : 'border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-white focus:border-orange-500'
              }`}
            />
          ))}
        </div>

        <button
          onClick={handleSubmit}
          disabled={tokenString.length !== 6 || loading}
          className="w-full bg-orange-600 hover:bg-orange-700 text-white py-4.5 rounded-2xl font-black uppercase text-xs tracking-[0.2em] shadow-xl shadow-orange-600/30 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
        >
          {loading ? (
            <span>MEMVALIDASI KE SERVER...</span>
          ) : (
            <>
              <Sparkles size={16} />
              <span>MULAI UJIAN SEKARANG</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default TokenInputOTP;
