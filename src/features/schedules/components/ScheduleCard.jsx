import {
  Calendar,
  Key,
  User,
  Edit3,
  Trash2,
  BookOpen,
  ShieldCheck,
  Unlock,
  Users,
  FileSpreadsheet,
  Check,
  AlertCircle,
} from 'lucide-react';
import { isExamReadyForStudent } from '../constants';
import { getCollabProgressList } from '../utils';

function getStatusBadge(status) {
  switch (status) {
    case 'pending_selection':
      return (
        <span className="bg-yellow-100 text-yellow-700 px-3 py-1 rounded-full text-[9px] font-black uppercase flex items-center gap-1">
          <AlertCircle size={10} /> Tunggu Soal
        </span>
      );
    case 'waiting_validation':
      return (
        <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-[9px] font-black uppercase flex items-center gap-1">
          <ShieldCheck size={10} /> Tunggu Verifikasi
        </span>
      );
    case 'ready':
    case 'validated':
      return (
        <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-[9px] font-black uppercase flex items-center gap-1">
          <Check size={10} /> Siap Ujian
        </span>
      );
    default:
      return (
        <span className="bg-slate-100 text-slate-500 px-3 py-1 rounded-full text-[9px] font-black uppercase">
          {status}
        </span>
      );
  }
}

function getFinalQuota(exam) {
  const value = exam.teacher_quota ?? exam.exams?.target_question_count ?? 0;
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function isMyTaskDone(exam) {
  if (!exam.exams || exam.exams.status !== 'pending_selection') return false;
  const filled = Number.isFinite(Number(exam.my_question_count))
    ? Number(exam.my_question_count)
    : 0;
  return filled >= getFinalQuota(exam);
}

export function ScheduleCard({
  exam,
  userRole,
  formatWIB,
  onEdit,
  onDelete,
  onOpenSelectQuestions,
  onVerify,
  onUnlockUH,
  onOpenParticipants,
  onOpenResults,
}) {
  const tokenActive = isExamReadyForStudent(exam.exams?.status);
  const progressList = exam.teacher_progress_list || [];
  const showProgress =
    userRole === 'admin' &&
    exam.exams?.status === 'pending_selection' &&
    progressList.length > 0;
  const collabProgressList = getCollabProgressList(
    progressList,
    exam.teacher_id
  );
  const showCollabProgress = showProgress && collabProgressList.length > 0;
  const myCount = Number.isFinite(Number(exam.my_question_count))
    ? Number(exam.my_question_count)
    : 0;
  const finalQuota = getFinalQuota(exam);

  return (
    <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] shadow-sm border border-slate-200 dark:border-zinc-800 relative group transition-all hover:border-orange-500 overflow-hidden">
      <div className="absolute top-0 right-0 bg-orange-100 dark:bg-orange-900/30 text-orange-600 font-black text-[10px] px-4 py-2 rounded-bl-2xl z-10">
        {exam.exams?.type || 'UH'}
      </div>

      <div className="absolute top-10 right-8 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        {(userRole === 'admin' ||
          (userRole === 'guru' && exam.exams?.type === 'UH')) && (
          <>
            <button
              onClick={() => onEdit(exam)}
              className="p-2 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 transition-colors"
            >
              <Edit3 size={16} />
            </button>
            <button
              onClick={() => onDelete(exam)}
              className="p-2 bg-red-50 text-red-500 rounded-xl hover:bg-red-100 transition-colors"
            >
              <Trash2 size={16} />
            </button>
          </>
        )}
      </div>

      <div className="flex justify-between items-start mb-6 pt-2">
        {getStatusBadge(exam.exams?.status)}

        {['PAS/PAT', 'SAJ'].includes(exam.exams?.type) && (
          <span className="bg-slate-100 dark:bg-zinc-800 px-3 py-1 rounded-lg text-[9px] font-bold text-slate-500 uppercase italic">
            {exam.session_no === 0 ? 'Semua Sesi' : `Sesi ${exam.session_no}`}
          </span>
        )}
      </div>

      <h3 className="text-xl font-black mb-1 uppercase italic leading-tight pr-10 truncate">
        {exam.exams?.title}
      </h3>

      <p
        className="text-orange-600 font-black text-xs mb-6 uppercase truncate"
        title={
          ['UH', 'PTS'].includes(exam.exams?.type)
            ? exam.classes?.name
            : exam.cluster_classes_text
        }
      >
        {exam.exams?.subjects?.name} |{' '}
        {['UH', 'PTS'].includes(exam.exams?.type)
          ? exam.classes?.name
          : exam.cluster_classes_text}
      </p>

      <div className="space-y-3 mb-8 text-slate-500 text-xs font-bold uppercase">
        <div className="flex items-center gap-3">
          <Calendar size={14} className="text-orange-500" /> {formatWIB(exam.start_time)}
        </div>
        <div className="flex items-center gap-3 font-mono">
          <Key size={14} className="text-orange-500" />
          <span className="text-zinc-900 dark:text-white tracking-widest">
            {exam.token}
          </span>
          <span
            className={`px-2 py-1 rounded-lg text-[8px] font-black uppercase tracking-wider ${
              tokenActive
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-slate-100 text-slate-500'
            }`}
          >
            {tokenActive ? 'Token Aktif' : 'Belum Aktif'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <User size={14} className="text-orange-500" />
          <span className="truncate">{exam.teachers?.full_name}</span>
        </div>
      </div>

      <div className="flex flex-col gap-2 border-t border-dashed border-zinc-200 dark:border-zinc-800 pt-6">
        {showCollabProgress && (
          <div className="w-full rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-900/40 px-4 py-3 text-[10px] font-bold uppercase">
            <div className="mb-2 text-slate-500 dark:text-zinc-400">Rekan Colab</div>
            <div className="space-y-1">
              {collabProgressList.map((teacher) => (
                <div
                  key={teacher.teacher_id || teacher.id || teacher.name}
                  className="flex justify-between"
                >
                  <span className="truncate">{teacher.name}</span>
                  <span className="text-slate-600 dark:text-zinc-300">
                    {(teacher.filled ?? 0)}/{(teacher.quota ?? 0)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        {userRole === 'admin' && exam.exams?.status === 'pending_selection' && (
          <div
            className={`w-full py-3 px-4 rounded-xl font-bold text-[10px] uppercase flex justify-between items-center mb-1 ${
              isMyTaskDone(exam)
                ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                : 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800'
            }`}
          >
            <span className="flex items-center gap-2 truncate pr-2">
              {isMyTaskDone(exam) ? (
                <Check size={14} className="shrink-0" />
              ) : (
                <AlertCircle size={14} className="shrink-0" />
              )}
              Progres: {exam.teachers?.full_name?.split(' ')[0] || 'Guru'}
            </span>
            <span className="text-xs whitespace-nowrap shrink-0">
              {myCount} / {finalQuota} Soal
            </span>
          </div>
        )}

        {userRole === 'guru' && exam.exams?.status === 'pending_selection' && (
          <button
            onClick={() => onOpenSelectQuestions(exam.id)}
            className="w-full bg-blue-600 hover:bg-blue-700 transition-colors text-white py-4 rounded-2xl font-black text-[10px] uppercase shadow-lg flex items-center justify-center gap-2"
          >
            <BookOpen size={14} />{' '}
            {exam.my_question_count > 0
              ? `Lanjutkan Pilih Soal (${exam.my_question_count})`
              : 'Pilih Soal'}
          </button>
        )}

        {userRole === 'admin' && exam.exams?.status === 'waiting_validation' && (
          <button
            onClick={() => onVerify(exam.exams?.id)}
            className="w-full bg-emerald-600 hover:bg-emerald-700 transition-colors text-white py-4 rounded-2xl font-black text-[10px] uppercase shadow-lg flex items-center justify-center gap-2"
          >
            <ShieldCheck size={14} /> Verifikasi Ujian
          </button>
        )}

        {(exam.exams?.status === 'validated' || exam.exams?.status === 'ready') &&
          userRole === 'guru' &&
          exam.exams?.type === 'UH' && (
            <button
              onClick={() => onUnlockUH(exam)}
              className="w-full bg-amber-500 hover:bg-amber-600 transition-colors text-white py-4 rounded-2xl font-black text-[10px] uppercase shadow-sm flex items-center justify-center gap-2 mb-1"
            >
              <Unlock size={14} /> Buka Kunci & Edit Soal
            </button>
          )}

        <button
          onClick={() => onOpenParticipants(exam.id)}
          className="w-full bg-slate-900 hover:bg-slate-800 text-white dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white transition-colors py-4 rounded-2xl font-black text-[10px] uppercase shadow-sm flex items-center justify-center gap-2"
        >
          <Users size={16} /> INFO PESERTA
        </button>

        <button
          onClick={() => onOpenResults(exam.id)}
          className="w-full bg-slate-900 hover:bg-slate-800 text-white dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white transition-colors py-4 rounded-2xl font-black text-[10px] uppercase shadow-sm flex items-center justify-center gap-2"
          title="Rekap Nilai & Analisis"
        >
          <FileSpreadsheet size={16} /> REKAP NILAI & ANALISIS
        </button>
      </div>
    </div>
  );
}
