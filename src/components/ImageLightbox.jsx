import React, { useState } from 'react';
import { X, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

const ImageLightbox = ({ src, alt = 'Gambar Soal', onClose }) => {
  const [scale, setScale] = useState(1);

  if (!src) return null;

  const handleZoomIn = () => setScale(prev => Math.min(prev + 0.3, 3));
  const handleZoomOut = () => setScale(prev => Math.max(prev - 0.3, 0.7));
  const handleReset = () => setScale(1);

  return (
    <div 
      className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex flex-col items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      {/* Action Header */}
      <div 
        className="absolute top-4 right-4 flex items-center gap-2 z-50"
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={handleZoomIn}
          aria-label="Perbesar Gambar"
          className="p-3 bg-zinc-800/80 hover:bg-zinc-700 text-white rounded-2xl backdrop-blur-md border border-white/10 transition-all active:scale-90"
        >
          <ZoomIn size={20} />
        </button>
        <button
          onClick={handleZoomOut}
          aria-label="Perkecil Gambar"
          className="p-3 bg-zinc-800/80 hover:bg-zinc-700 text-white rounded-2xl backdrop-blur-md border border-white/10 transition-all active:scale-90"
        >
          <ZoomOut size={20} />
        </button>
        <button
          onClick={handleReset}
          aria-label="Reset Ukuran"
          className="p-3 bg-zinc-800/80 hover:bg-zinc-700 text-white rounded-2xl backdrop-blur-md border border-white/10 transition-all active:scale-90"
        >
          <RotateCcw size={20} />
        </button>
        <button
          onClick={onClose}
          aria-label="Tutup"
          className="p-3 bg-orange-600 hover:bg-orange-700 text-white rounded-2xl shadow-lg shadow-orange-600/30 transition-all active:scale-90 ml-2"
        >
          <X size={20} />
        </button>
      </div>

      {/* Image Display */}
      <div 
        className="max-w-full max-h-[85vh] overflow-auto flex items-center justify-center p-2"
        onClick={e => e.stopPropagation()}
      >
        <img
          src={src}
          alt={alt}
          style={{ transform: `scale(${scale})`, transition: 'transform 0.2s ease-out' }}
          className="max-h-[80vh] max-w-[90vw] object-contain rounded-2xl shadow-2xl cursor-grab active:cursor-grabbing select-none"
        />
      </div>

      <p className="absolute bottom-6 text-zinc-400 font-bold text-xs uppercase tracking-widest pointer-events-none">
        Ketuk di luar gambar atau tombol silang untuk menutup
      </p>
    </div>
  );
};

export default ImageLightbox;
