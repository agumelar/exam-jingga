supabase menggunakan freetier jangan ubah logika jadi kita maksimalkan supabase freetier
untuk waktu menggunanakn WIB
workflow
admin :
    1. pengaturan logistik
        - tentukan sesi dan ruangan
        - print daftar hadir dan ddaftar peserta
        - prin kartu ujian
    2. menentukan PTS
        - admin menjadwalkan
        - guru memilih soal
        - admin verifikasi
        - ujian bisa dimulai
    3. menentukan PAS/PAT dan SAJ
        - admin menjadwalkan
        - guru memilih soal
        - admin verifikasi
        - ujian bisa dimulai
Guru : 
    membuat bank soal
    memilih sola
    untuk UH guru bisa menjadwalkan sendiiri dan memilih soal sendiri tanpa harus verifikasi admin

Siswa :
    memilih soal dan mengerjakan soal sesuai dengan kelas dan guru yg bersangkutan

Fitur
    - anti cheat, ter block hanya untuk ujian resmi (PAS/PAT dan SAJ) untuk UH dan PTS hanya ada peringatan aja
    - pengisian soal dan jadwal berdasarkan masing masing guru
    - untuk 1 mapel dengan beda guru di kelas yang sama berarti soalnya dibagi, berdasarkan sesuai dengan code yg sudah dibuat (untuk mapel produktif)