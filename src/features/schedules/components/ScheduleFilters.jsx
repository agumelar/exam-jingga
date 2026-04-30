import { Search, CalendarDays } from 'lucide-react';

export function ScheduleFilters({
  searchTerm,
  onSearchTermChange,
  dateFilter,
  onDateFilterChange,
}) {
  return (
    <div className="bg-white dark:bg-zinc-900 p-4 rounded-3xl border border-slate-100 dark:border-zinc-800 shadow-sm mb-8 flex flex-col sm:flex-row gap-4">
      <div className="flex-1 relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400">
          <Search size={18} />
        </div>
        <input
          type="text"
          placeholder="Cari nama ujian atau mapel..."
          value={searchTerm}
          onChange={(event) => onSearchTermChange(event.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white"
        />
      </div>

      <div className="w-full sm:w-56 relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400">
          <CalendarDays size={18} />
        </div>
        <select
          value={dateFilter}
          onChange={(event) => onDateFilterChange(event.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white appearance-none cursor-pointer"
        >
          <option value="Semua Ujian">Semua Waktu</option>
          <option value="Hari Ini">Jadwal Hari Ini</option>
        </select>
      </div>
    </div>
  );
}
