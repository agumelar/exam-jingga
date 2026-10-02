import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Plus, Trash2, Edit, X, BookOpen, Layers, ImageIcon, Loader2, User } from 'lucide-react';
import Swal from 'sweetalert2';
import imageCompression from 'browser-image-compression';

const BankSoal = () => {
  const [levels, setLevels] = useState([]);
  const [mySubjects, setMySubjects] = useState([]);
  const [teachers, setTeachers] = useState([]); 
  const [selectedLevel, setSelectedLevel] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedTeacher, setSelectedTeacher] = useState(''); 
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userRole, setUserRole] = useState('');
  const [myTeacherId, setMyTeacherId] = useState(null);
  
  const [showModal, setShowModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(null);
  const [editingId, setEditingId] = useState(null);

  const initialForm = {
    question_text: '', question_image: '',
    option_a: '', image_a: '', option_b: '', image_b: '',
    option_c: '', image_c: '', option_d: '', image_d: '',
    option_e: '', image_e: '', correct_answer: 'A'
  };
  const [formData, setFormData] = useState(initialForm);

  useEffect(() => { fetchInitialData(); }, []);

  const fetchInitialData = async () => {
    // SUNTIKAN: Ambil session manual dari localStorage
    const userSession = localStorage.getItem('user_session');
    if (!userSession) return window.location.href = '/login';

    const userData = JSON.parse(userSession);
    const role = userData.role.toLowerCase();
    setUserRole(role);
    setMyTeacherId(userData.id);

    // Ambil Semua Penugasan untuk filter
    let query = supabase.from('teacher_assignments').select(`
      subject_id, 
      teacher_id, 
      subjects(id, name), 
      classes(name), 
      teachers(id, full_name)
    `);

    // Jika GURU, batasi hanya penugasannya sendiri
    if (role === 'guru') {
      query = query.eq('teacher_id', userData.id);
    }
    
    const { data: assignData } = await query;
    if (assignData) {
      setMySubjects(assignData);
      
      // Ambil Jenjang Unik (Angka depan dari nama kelas, misal "10 RPL 1" jadi 10)
      const uniqueLevels = Array.from(new Set(assignData.map(a => parseInt(a.classes.name.split(' ')[0]))))
        .filter(l => !isNaN(l))
        .sort((a, b) => a - b);
      setLevels(uniqueLevels);
      
      if (role !== 'guru') {
        const uniqueTeachers = Array.from(new Set(assignData.map(a => a.teacher_id)))
          .map(id => {
            const match = assignData.find(a => a.teacher_id === id);
            return match ? match.teachers : null;
          }).filter(Boolean);
        setTeachers(uniqueTeachers);
      } else {
        setSelectedTeacher(userData.id); // Guru otomatis terkunci ke dirinya sendiri
      }
    }
  };

  const fetchQuestions = async (subjectId, level, teacherId) => {
    if (!subjectId || !level || !teacherId) return;
    setLoading(true);
    const { data } = await supabase.from('questions')
      .select('*')
      .eq('subject_id', subjectId)
      .eq('level', level)
      .eq('created_by', teacherId)
      .order('created_at', { ascending: true });
    
    setQuestions(data || []);
    setLoading(false);
  };

  // Logic filter Mapel berdasarkan jenjang yang dipilih
  const availableSubjects = Array.from(new Set(mySubjects
    .filter(a => parseInt(a.classes.name.split(' ')[0]) === parseInt(selectedLevel))
    .map(a => a.subject_id)))
    .map(id => mySubjects.find(a => a.subject_id === id).subjects);

  // Logic filter Guru berdasarkan Mapel & Jenjang (Hanya untuk Admin)
  const availableTeachers = teachers.filter(t => 
    mySubjects.some(a => 
      a.teacher_id === t.id && 
      a.subject_id === selectedSubject && 
      parseInt(a.classes.name.split(' ')[0]) === parseInt(selectedLevel)
    )
  );

  const handleFileUpload = async (e, field) => {
    const file = e.target.files[0];
    if (!file) return;
    setIsUploading(field);
    try {
      const options = { maxSizeMB: 0.1, maxWidthOrHeight: 800, useWebWorker: true, initialQuality: 0.7 };
      const compressedFile = await imageCompression(file, options);
      const fileExt = file.name.split('.').pop();
      const fileName = `${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExt}`;
      const filePath = `${myTeacherId}/${fileName}`;
      const { error: uploadError } = await supabase.storage.from('question-images').upload(filePath, compressedFile);
      if (uploadError) throw uploadError;
      const { data } = supabase.storage.from('question-images').getPublicUrl(filePath);
      setFormData(prev => ({ ...prev, [field]: data.publicUrl }));
    } catch (error) { Swal.fire('Gagal!', error.message, 'error'); } 
    finally { setIsUploading(null); }
  };

  const deleteOldFile = async (url) => {
    if (!url) return;
    const path = url.split('/public/question-images/')[1];
    if (path) await supabase.storage.from('question-images').remove([path]);
  };

  const handleDelete = async (q) => {
    const { isConfirmed } = await Swal.fire({
      title: 'Hapus Soal?',
      text: "Data dan file di storage akan dihapus permanen!",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ea580c'
    });
    if (isConfirmed) {
      const images = [q.question_image, q.image_a, q.image_b, q.image_c, q.image_d, q.image_e];
      for (const imgUrl of images) { if (imgUrl) await deleteOldFile(imgUrl); }
      await supabase.from('questions').delete().eq('id', q.id);
      fetchQuestions(selectedSubject, selectedLevel, selectedTeacher);
      Swal.fire('Terhapus!', 'Soal dibersihkan.', 'success');
    }
  };

  const handleSaveQuestion = async (e) => {
    e.preventDefault();
    if (!selectedSubject || !selectedLevel || !selectedTeacher) {
      return Swal.fire('Gagal!', 'Lengkapi filter terlebih dahulu.', 'error');
    }
    setIsSaving(true);
    const payload = { ...formData, subject_id: selectedSubject, level: Number(selectedLevel), created_by: selectedTeacher };
    try {
      let result;
      if (editingId) result = await supabase.from('questions').update(payload).eq('id', editingId);
      else result = await supabase.from('questions').insert([payload]);
      if (result.error) throw result.error;
      setShowModal(false);
      setEditingId(null);
      setFormData(initialForm);
      fetchQuestions(selectedSubject, selectedLevel, selectedTeacher);
      Swal.fire('Berhasil!', 'Bank soal diperbarui.', 'success');
    } catch (error) { Swal.fire('Gagal Simpan!', error.message, 'error'); } 
    finally { setIsSaving(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex transition-colors duration-300 font-sans text-left text-slate-800 dark:text-zinc-100">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        <header className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="text-left">
            <h2 className="text-3xl font-black italic uppercase tracking-tighter">Bank Soal</h2>
            <p className="text-slate-500 font-medium italic text-sm">Kelola soal per Guru & Mapel</p>
          </div>
          {selectedSubject && selectedLevel && selectedTeacher && (
            <button onClick={() => { setEditingId(null); setFormData(initialForm); setShowModal(true); }} className="bg-orange-600 text-white px-6 py-3 rounded-2xl font-black shadow-lg hover:bg-orange-700 transition-all uppercase text-xs flex items-center gap-2">
              <Plus size={18} /> Tambah Soal
            </button>
          )}
        </header>

        {/* TRIPLE FILTER: LEVEL, MAPEL, GURU */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8 text-left">
            <div className="bg-white dark:bg-zinc-900 p-4 rounded-2xl shadow-sm border border-slate-100 dark:border-zinc-800">
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block ml-1 tracking-widest"><Layers size={12} className="inline mr-1"/> Jenjang Kelas</label>
                <select className="w-full bg-transparent font-bold outline-none cursor-pointer" value={selectedLevel} onChange={(e) => { setSelectedLevel(e.target.value); setSelectedSubject(''); setSelectedTeacher(userRole === 'guru' ? myTeacherId : ''); setQuestions([]); }}>
                <option value="">-- Pilih Jenjang --</option>
                {levels.map(l => <option key={l} value={l} className="text-black">Kelas {l}</option>)}
                </select>
            </div>
            <div className="bg-white dark:bg-zinc-900 p-4 rounded-2xl shadow-sm border border-slate-100 dark:border-zinc-800">
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block ml-1 tracking-widest"><BookOpen size={12} className="inline mr-1"/> Mata Pelajaran</label>
                <select className="w-full bg-transparent font-bold outline-none cursor-pointer" disabled={!selectedLevel} value={selectedSubject} onChange={(e) => { setSelectedSubject(e.target.value); if(userRole === 'guru') fetchQuestions(e.target.value, selectedLevel, myTeacherId); else { setSelectedTeacher(''); setQuestions([]); } }}>
                <option value="">-- Pilih Mapel --</option>
                {availableSubjects.map(s => <option key={s.id} value={s.id} className="text-black">{s.name}</option>)}
                </select>
            </div>
            {userRole !== 'guru' && (
                <div className="bg-white dark:bg-zinc-900 p-4 rounded-2xl shadow-sm border-2 border-orange-500/20">
                    <label className="text-[10px] font-black uppercase text-orange-500 mb-2 block ml-1 tracking-widest"><User size={12} className="inline mr-1"/> Guru Pengampu</label>
                    <select className="w-full bg-transparent font-bold outline-none cursor-pointer" disabled={!selectedSubject} value={selectedTeacher} onChange={(e) => { setSelectedTeacher(e.target.value); if(e.target.value) fetchQuestions(selectedSubject, selectedLevel, e.target.value); }}>
                    <option value="">-- Pilih Guru --</option>
                    {availableTeachers.map(t => <option key={t.id} value={t.id} className="text-black">{t.full_name}</option>)}
                    </select>
                </div>
            )}
        </div>

        {/* DAFTAR SOAL */}
        <div className="space-y-6">
          {loading ? (
             <div className="py-20 text-center animate-pulse font-black text-orange-500 uppercase italic">Memuat Soal...</div>
          ) : !selectedTeacher || !selectedSubject ? (
             <div className="py-24 text-center text-slate-400 font-bold italic bg-white dark:bg-zinc-900 rounded-[3rem] border-2 border-dashed border-slate-200 dark:border-zinc-800">
                {userRole === 'guru' ? 'Pilih Jenjang & Mapel untuk mengelola bank soal Anda.' : 'Pilih Jenjang, Mapel, dan Guru untuk melihat bank soal.'}
             </div>
          ) : questions.length === 0 ? (
             <div className="py-24 text-center text-slate-400 font-bold italic bg-white dark:bg-zinc-900 rounded-[3rem] border border-slate-100 dark:border-zinc-800">
                Belum ada soal untuk filter ini bro. Klik "Tambah Soal" di atas.
             </div>
          ) : (
            questions.map((q, idx) => (
              <div key={q.id} className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 shadow-sm text-left relative group hover:border-orange-500/50 transition-all">
                <div className="flex justify-between items-start mb-6">
                  <span className="bg-orange-600 text-white px-4 py-1 rounded-full text-[10px] font-black italic uppercase tracking-widest">SOAL MASTER #{idx + 1}</span>
                  <div className="flex gap-2">
                    <button onClick={() => { setEditingId(q.id); setFormData(q); setShowModal(true); }} className="p-2 text-slate-300 hover:text-blue-500 transition-colors"><Edit size={18}/></button>
                    <button onClick={() => handleDelete(q)} className="p-2 text-slate-300 hover:text-red-500 transition-colors"><Trash2 size={18}/></button>
                  </div>
                </div>
                <p className="text-lg font-bold dark:text-white mb-6 leading-relaxed">{q.question_text}</p>
                {q.question_image && <img src={q.question_image} className="max-h-64 rounded-2xl mb-8 border border-slate-100 shadow-md" alt="soal" />}
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {['a','b','c','d','e'].map(opt => (
                    <div key={opt} className={`p-5 rounded-2xl border-2 transition-all ${q.correct_answer === opt.toUpperCase() ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-900/10' : 'border-slate-50 dark:border-zinc-800'}`}>
                      <div className="flex items-center gap-4 mb-3">
                          <span className={`w-10 h-10 rounded-full flex items-center justify-center font-black text-xs ${q.correct_answer === opt.toUpperCase() ? 'bg-emerald-500 text-white' : 'bg-slate-100 dark:bg-zinc-800 text-slate-500'}`}>{opt.toUpperCase()}</span>
                          <span className="text-sm font-bold dark:text-zinc-200">{q[`option_${opt}`]}</span>
                      </div>
                      {q[`image_${opt}`] && <img src={q[`image_${opt}`]} className="h-24 rounded-xl ml-14 object-cover border border-slate-100 shadow-sm" alt={`opsi ${opt}`} />}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* MODAL INPUT SOAL */}
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
            <div className="bg-white dark:bg-zinc-950 w-full max-w-4xl rounded-[3rem] p-10 shadow-2xl my-auto text-left relative">
              <button onClick={() => setShowModal(false)} className="absolute top-8 right-8 p-2 hover:text-red-500 dark:text-white"><X size={24}/></button>
              <h3 className="text-2xl font-black dark:text-white uppercase italic tracking-tighter mb-8 border-l-8 border-orange-600 pl-4">{editingId ? 'Update Soal' : 'Soal Baru'}</h3>
              
              <form onSubmit={handleSaveQuestion} className="space-y-8">
                <div className="space-y-4">
                  <label className="text-[10px] font-black uppercase text-slate-400 ml-2 tracking-widest italic">Konten Pertanyaan</label>
                  <textarea required className="w-full bg-slate-50 dark:bg-zinc-900 p-8 rounded-[2rem] dark:text-white border-none shadow-inner font-bold text-lg" rows="4" placeholder="Tulis soal di sini..." value={formData.question_text} onChange={e => setFormData({...formData, question_text: e.target.value})} />
                  <div className="flex items-center gap-4">
                    <label className="cursor-pointer bg-slate-100 dark:bg-zinc-800 px-6 py-3 rounded-2xl text-[10px] font-black uppercase flex items-center gap-2 hover:bg-orange-600 hover:text-white transition-all dark:text-white">
                      {isUploading === 'question_image' ? <Loader2 className="animate-spin" size={16}/> : <ImageIcon size={16}/>} Unggah Gambar Soal
                      <input type="file" className="hidden" accept="image/*" onChange={(e) => handleFileUpload(e, 'question_image')} />
                    </label>
                    {formData.question_image && <div className="relative"><img src={formData.question_image} className="h-16 rounded-xl border-2 border-orange-500" /><button type="button" onClick={()=>{deleteOldFile(formData.question_image); setFormData({...formData, question_image:''});}} className="absolute -top-3 -right-3 bg-red-500 text-white rounded-full p-1 shadow-lg"><X size={12}/></button></div>}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {['a','b','c','d','e'].map(opt => (
                    <div key={opt} className="space-y-3 bg-slate-50 dark:bg-zinc-900/50 p-6 rounded-3xl border border-slate-100 dark:border-zinc-800">
                      <div className="flex items-center gap-3">
                         <span className="w-8 h-8 rounded-full bg-orange-600 text-white flex items-center justify-center font-black text-xs">{opt.toUpperCase()}</span>
                         <input type="text" className="flex-1 bg-transparent dark:text-white border-none outline-none font-bold" placeholder={`Isi pilihan ${opt.toUpperCase()}...`} value={formData[`option_${opt}`]} onChange={e => setFormData({...formData, [`option_${opt}`]: e.target.value})} />
                         <label className="cursor-pointer p-2 hover:text-orange-600 dark:text-zinc-500 transition-colors">
                            {isUploading === `image_${opt}` ? <Loader2 className="animate-spin" size={20}/> : <ImageIcon size={20}/>}
                            <input type="file" className="hidden" accept="image/*" onChange={(e) => handleFileUpload(e, `image_${opt}`)} />
                         </label>
                      </div>
                      {formData[`image_${opt}`] && <div className="relative w-max ml-11"><img src={formData[`image_${opt}`]} className="h-14 rounded-lg border" /><button type="button" onClick={()=>{deleteOldFile(formData[`image_${opt}`]); setFormData({...formData, [`image_${opt}`]:''});}} className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5"><X size={10}/></button></div>}
                    </div>
                  ))}
                  
                  <div className="md:col-span-2">
                    <label className="text-[10px] font-black uppercase text-orange-600 ml-2 mb-3 block tracking-widest italic text-center">Tentukan Kunci Jawaban</label>
                    <div className="flex justify-center gap-3">
                        {['A','B','C','D','E'].map(k => (
                            <button key={k} type="button" onClick={() => setFormData({...formData, correct_answer: k})} className={`w-14 h-14 rounded-2xl font-black text-lg transition-all ${formData.correct_answer === k ? 'bg-emerald-500 text-white scale-110 shadow-lg shadow-emerald-500/20' : 'bg-slate-100 dark:bg-zinc-800 text-slate-400'}`}>{k}</button>
                        ))}
                    </div>
                  </div>
                </div>

                <button type="submit" disabled={isSaving || isUploading} className="w-full bg-slate-900 dark:bg-white dark:text-black text-white py-6 rounded-[2rem] font-black uppercase tracking-[0.3em] shadow-2xl disabled:opacity-50 transition-all hover:scale-[1.02] text-sm">
                  {isSaving ? "SEDANG MENYIMPAN..." : editingId ? "UPDATE SOAL" : "SIMPAN KE BANK SOAL"}
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default BankSoal;