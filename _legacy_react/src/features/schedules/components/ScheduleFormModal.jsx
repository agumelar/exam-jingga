import { X, RefreshCw } from 'lucide-react';

export function ScheduleFormModal({
  userRole,
  editingId,
  formData,
  setFormData,
  availableLevels,
  availableClasses,
  availableSubjects,
  availableTeachersForClass,
  generateToken,
  onSubmit,
  onClose,
  saving,
  loading,
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto font-sans">
      <div className="bg-white dark:bg-zinc-950 w-full max-w-4xl rounded-[3rem] p-10 shadow-2xl text-left relative text-slate-900 dark:text-white font-bold border border-zinc-200 dark:border-zinc-800">
        <button
          onClick={onClose}
          className="absolute top-8 right-8 p-2 text-zinc-400 hover:text-red-500 transition-colors"
        >
          <X size={24} />
        </button>
        <h3 className="text-2xl font-black uppercase italic mb-8 border-l-8 border-orange-600 pl-4 tracking-tighter">
          Konfigurasi {formData.type}
        </h3>

        <form onSubmit={onSubmit} className="space-y-4">
          {userRole === 'admin' && !editingId && (
            <div className="grid grid-cols-3 gap-3 mb-6">
              {['PTS', 'PAS/PAT', 'SAJ'].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() =>
                    setFormData({
                      ...formData,
                      type,
                      sub_type: '',
                      title: '',
                      class_id: '',
                    })
                  }
                  className={`py-4 rounded-2xl font-black text-[10px] transition-all border ${
                    formData.type === type
                      ? 'bg-orange-600 text-white border-orange-600 shadow-lg'
                      : 'bg-slate-50 dark:bg-zinc-900 text-slate-500 border-slate-200 dark:border-zinc-800'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          )}

          {formData.type === 'UH' && (
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                Nama Ujian
              </label>
              <input
                required
                className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none font-bold shadow-inner outline-none focus:ring-2 focus:ring-orange-500"
                placeholder="Cth: Ulangan Harian Bab 1"
                value={formData.title}
                onChange={(event) =>
                  setFormData({ ...formData, title: event.target.value })
                }
              />
            </div>
          )}

          {(formData.type === 'PTS' || formData.type === 'PAS/PAT') && (
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                Jenis Semester
              </label>
              <select
                required
                className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500"
                value={formData.sub_type}
                onChange={(event) =>
                  setFormData({ ...formData, sub_type: event.target.value })
                }
              >
                <option value="">-- Pilih Jenis/Semester --</option>
                {formData.type === 'PTS' ? (
                  <>
                    <option value="PTS Ganjil">PTS Ganjil</option>
                    <option value="PTS Genap">PTS Genap</option>
                  </>
                ) : (
                  <>
                    <option value="Penilaian Akhir Semester">PAS (Ganjil)</option>
                    <option value="Penilaian Akhir Tahun">PAT (Genap)</option>
                  </>
                )}
              </select>
            </div>
          )}

          {!editingId && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                  Tingkat Jenjang
                </label>
                <select
                  required
                  className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500"
                  value={formData.level}
                  onChange={(event) =>
                    setFormData({
                      ...formData,
                      level: event.target.value,
                      class_id: '',
                      subject_id: '',
                      teacher_id: '',
                    })
                  }
                >
                  <option value="">-- Pilih Jenjang --</option>
                  {availableLevels.map((level) => (
                    <option key={level} value={level}>
                      Kelas {level}
                    </option>
                  ))}
                </select>
              </div>

              {(formData.type === 'UH' || formData.type === 'PTS') && (
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                    Pilih Kelas
                  </label>
                  <select
                    required
                    className="w-full bg-orange-50 dark:bg-orange-900/20 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500"
                    value={formData.class_id}
                    onChange={(event) =>
                      setFormData({
                        ...formData,
                        class_id: event.target.value,
                        teacher_id: '',
                      })
                    }
                  >
                    <option value="">-- Pilih Kelas --</option>
                    {availableClasses.map((classItem) => (
                      <option key={classItem.id} value={classItem.id}>
                        {classItem.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                  Mata Pelajaran
                </label>
                <select
                  required
                  disabled={!formData.level}
                  className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50"
                  value={formData.subject_id}
                  onChange={(event) =>
                    setFormData({
                      ...formData,
                      subject_id: event.target.value,
                      teacher_id: '',
                    })
                  }
                >
                  <option value="">-- Pilih Mapel --</option>
                  {availableSubjects.map((subject) => (
                    <option key={subject.id} value={subject.id}>
                      {subject.name}
                    </option>
                  ))}
                </select>
              </div>

              {userRole === 'admin' && formData.type === 'PTS' && (
                <div className="space-y-1 md:col-span-3">
                  <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                    Guru Pengampu
                  </label>
                  <select
                    required
                    disabled={!formData.class_id || !formData.subject_id}
                    className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50"
                    value={formData.teacher_id}
                    onChange={(event) =>
                      setFormData({ ...formData, teacher_id: event.target.value })
                    }
                  >
                    <option value="">-- Pilih Guru Penanggung Jawab --</option>
                    {availableTeachersForClass.map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {teacher.full_name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                Waktu Mulai Ujian
              </label>
              <input
                type="datetime-local"
                required
                className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500"
                value={formData.start_time}
                onChange={(event) =>
                  setFormData({ ...formData, start_time: event.target.value })
                }
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                Token Akses
              </label>
              <div className="relative">
                <input
                  className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none font-black tracking-widest text-orange-600 outline-none"
                  value={formData.token}
                  readOnly
                />
                <button
                  type="button"
                  onClick={generateToken}
                  className="absolute right-4 top-4 text-zinc-400 hover:text-orange-600 transition-colors"
                >
                  <RefreshCw size={18} />
                </button>
              </div>
            </div>
          </div>

          <div
            className={`grid ${
              ['PAS/PAT', 'SAJ'].includes(formData.type)
                ? 'grid-cols-3'
                : 'grid-cols-2'
            } gap-4`}
          >
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                Durasi (Menit)
              </label>
              <input
                type="number"
                required
                min="1"
                className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none shadow-inner outline-none focus:ring-2 focus:ring-orange-500"
                value={formData.duration}
                onChange={(event) =>
                  setFormData({ ...formData, duration: event.target.value })
                }
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                Target Soal
              </label>
              <input
                type="number"
                required
                min="1"
                className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none shadow-inner outline-none focus:ring-2 focus:ring-orange-500"
                value={formData.target_question_count}
                onChange={(event) =>
                  setFormData({
                    ...formData,
                    target_question_count: event.target.value,
                  })
                }
              />
            </div>

            {['PAS/PAT', 'SAJ'].includes(formData.type) && (
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">
                  Sesi Ujian
                </label>
                <select
                  required
                  className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500"
                  value={formData.session_no}
                  onChange={(event) =>
                    setFormData({ ...formData, session_no: event.target.value })
                  }
                >
                  <option value="Semua Sesi">Semua Sesi</option>
                  <option value="1">Sesi 1</option>
                  <option value="2">Sesi 2</option>
                  <option value="3">Sesi 3</option>
                </select>
              </div>
            )}
          </div>

          <div className="pt-6">
            <button
              type="submit"
              disabled={saving || loading}
              className="w-full bg-orange-600 text-white py-5 rounded-2xl font-black uppercase tracking-[0.2em] shadow-lg transition-all hover:bg-orange-700 active:scale-[0.98] disabled:opacity-50 flex justify-center items-center gap-2"
            >
              {saving ? 'MEMPROSES...' : 'SIMPAN JADWAL UJIAN'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
