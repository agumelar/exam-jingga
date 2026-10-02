# 📋 Pemetaan Data Guru Exam Jingga & Keterkaitan Data Admin Pusat (SDP)

Dokumen ini memuat daftar lengkap **47 Data Guru / GTK** yang ada pada basis data **Exam Jingga (CBT)** beserta pemetaan akun login lokal, kontribusi butir soal di Bank Soal, dan keterkaitan identitas dengan **School Data Platform (SDP)** (`https://data-admin.smkn1rongga.sch.id`) dan **Keycloak SSO** (`https://sso.smkn1rongga.sch.id`).

---

## 🏛️ Status Keterkaitan Identitas: 100% TERHUBUNG SSO 🟢

Seluruh data guru di database CBT telah memiliki **UUID SSO v5/v4** aktif yang konsisten dengan Single Source of Truth sekolah. Seluruh relasi butir soal di Bank Soal tetap melekat pada profil guru masing-masing.

---

## 📊 Tabel Rekapitulasi Data Guru & Keterkaitan Akun SSO

| No | Nama Lengkap Guru & Gelar | NIP / Identitas | Email Sekolah Resmi (`@smkn1rongga.sch.id`) | Akun Login CBT | Level Role | Butir Soal | Identitas SSO Keycloak (`sso_id`) |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | **ADE SANDI, S.Pd.,  ** | `-` | `adesandi@smkn1rongga.sch.id` | `adesandi` | Guru | 75 Soal | 🟢 **Terhubung** (`5dff97ee...65da`) |
| 2 | **AGNIA FILA ANISA, SP** | `-` | `agniafila@smkn1rongga.sch.id` | `agniafila` | Guru | 70 Soal | 🟢 **Terhubung** (`1e30ade1...a91a`) |
| 3 | **AGUS WALUYO, M.Ag** | `-` | `aguswaluyo@smkn1rongga.sch.id` | `aguswaluyo` | Guru | 80 Soal | 🟢 **Terhubung** (`da011e0a...227d`) |
| 4 | **ANEU NURBAYANTI, SST., ** | `-` | `aneu@smkn1rongga.sch.id` | `aneu` | Guru | 20 Soal | 🟢 **Terhubung** (`5252a6a6...5125`) |
| 5 | **ASEP AGUS SOLEH, S.Sos, ** | `-` | `asepagussoleh@smkn1rongga.sch.id` | `asepagussoleh` | Guru | 159 Soal | 🟢 **Terhubung** (`d33a4a23...10c2`) |
| 6 | **ASEP DEDE NURDIAWAN, ST., ** | `-` | `asepdn@smkn1rongga.sch.id` | `asepdn` | Guru | 65 Soal | 🟢 **Terhubung** (`031ab47b...c1ac`) |
| 7 | **ASEP HILMAN, ,S.Pd** | `-` | `asephilman@smkn1rongga.sch.id` | `asephilman` | Guru | 80 Soal | 🟢 **Terhubung** (`a351b7d5...2315`) |
| 8 | **ASEP KUSNADI PERMANA, M.Pd.,  ** | `-` | `asepkp@smkn1rongga.sch.id` | `asepkp` | Guru | 80 Soal | 🟢 **Terhubung** (`c911fb8c...f450`) |
| 9 | **Administrator Sekolah** | `-` | `admin@smkn1rongga.sch.id` | `admin` | Platform_admin | 1 Soal | 🟢 **Terhubung** (`611339bb...c44e`) |
| 10 | **Agung Gumelar Saputra** | `199306012022211013` | `gumelar@smkn1rongga.sch.id` | `gumelar` | Guru | 24 Soal | 🟢 **Terhubung** (`0b1d6349...f83a`) |
| 11 | **BENNY SURYA KOMARA, S.Pd** | `-` | `bsuryakomara@smkn1rongga.sch.id` | `bsuryakomara` | Guru | 100 Soal | 🟢 **Terhubung** (`1b95404d...bd09`) |
| 12 | **Bpk. Guru Pengajar, S.Kom** | `-` | `guru@smkn1rongga.sch.id` | `guru` | Guru | 3 Soal | 🟢 **Terhubung** (`22a353e8...90e2`) |
| 13 | **DEVIA PUTRI, S.Kom** | `-` | `deviaputri@smkn1rongga.sch.id` | `deviaputri` | Guru | 35 Soal | 🟢 **Terhubung** (`3e2f79d9...cf43`) |
| 14 | **DIKI ABDUL AZIZ, S.Kom** | `-` | `dikiabdulaziz@smkn1rongga.sch.id` | `dikiabdulaziz` | Guru | 30 Soal | 🟢 **Terhubung** (`e84fd364...11d2`) |
| 15 | **DIMAN RAHMAT, S.Kom** | `-` | `dimanrahmat@smkn1rongga.sch.id` | `dimanrahmat` | Guru | 25 Soal | 🟢 **Terhubung** (`77d394f0...482a`) |
| 16 | **DZUL KARUNIA AF, S.Pd., ** | `-` | `dzulkaf@smkn1rongga.sch.id` | `dzulkaf` | Guru | 160 Soal | 🟢 **Terhubung** (`0451bb1b...c29b`) |
| 17 | **Dhafika Mutiara** | `-` | `dhavika@smkn1rongga.sch.id` | `dhavika` | Guru | 40 Soal | 🟢 **Terhubung** (`57e0225e...3507`) |
| 18 | **ENCEP GUNAEPI,ST,  ** | `-` | `encepgunaepi@smkn1rongga.sch.id` | `encepgunaepi` | Guru | 41 Soal | 🟢 **Terhubung** (`75073fe2...8ce2`) |
| 19 | **ENDANG BASUNI, S.Sos.I** | `-` | `endangbasuni@smkn1rongga.sch.id` | `endangbasuni` | Guru | 0 Soal | 🟢 **Terhubung** (`35628e1b...e586`) |
| 20 | **ERNA ARIANTI, S.Pd.I** | `-` | `ernaarianti@smkn1rongga.sch.id` | `ernaarianti` | Guru | 87 Soal | 🟢 **Terhubung** (`7f883ae9...9deb`) |
| 21 | **HANI SURYANI, S.S., ** | `-` | `hani@smkn1rongga.sch.id` | `hani` | Guru | 100 Soal | 🟢 **Terhubung** (`18829866...3fea`) |
| 22 | **HENDRA, SP** | `-` | `hendra@smkn1rongga.sch.id` | `hendra` | Guru | 60 Soal | 🟢 **Terhubung** (`9a2b4ba8...22a9`) |
| 23 | **HENDRICK FIRGIANTISNA, S.Pd** | `-` | `hendrick@smkn1rongga.sch.id` | `hendrick` | Guru | 80 Soal | 🟢 **Terhubung** (`18ee0197...2305`) |
| 24 | **HERMAN, ST** | `-` | `herman@smkn1rongga.sch.id` | `herman` | Guru | 40 Soal | 🟢 **Terhubung** (`b7b38b33...7a0e`) |
| 25 | **HUSAM JUNDULOH, S.Tr.Kom** | `-` | `husamjunduloh@smkn1rongga.sch.id` | `husamjunduloh` | Guru | 58 Soal | 🟢 **Terhubung** (`82f2620b...851c`) |
| 26 | **IMAN NOORROKHMAN, S.Pd.,   ** | `-` | `imannoorrokhman@smkn1rongga.sch.id` | `imannoorrokhman` | Guru | 40 Soal | 🟢 **Terhubung** (`fbacfdb6...3ca9`) |
| 27 | **IMAS HETI PARIDA, S.Pd** | `-` | `imas@smkn1rongga.sch.id` | `imas` | Guru | 75 Soal | 🟢 **Terhubung** (`c41d59e7...7762`) |
| 28 | **JANJAN NURJAMAN, S.Kom** | `-` | `janjan@smkn1rongga.sch.id` | `janjan` | Guru | 25 Soal | 🟢 **Terhubung** (`992f3545...99bd`) |
| 29 | **Kurikulum Jingga** | `-` | `kurikulum@smkn1rongga.sch.id` | `kurikulum` | Kurikulum | 0 Soal | 🟢 **Terhubung** (`cfc0c5a8...fd4a`) |
| 30 | **LARAS AI NURFATWA, S.Pd., ** | `-` | `laras@smkn1rongga.sch.id` | `laras` | Guru | 100 Soal | 🟢 **Terhubung** (`0e89896d...c588`) |
| 31 | **LUCKY ANDRIANA SAPUTRA, S.Kom** | `-` | `lucky@smkn1rongga.sch.id` | `lucky` | Guru | 20 Soal | 🟢 **Terhubung** (`de7f32dc...6cd1`) |
| 32 | **MAYA NADIA SEPTIANI, S.Sos** | `-` | `maya@smkn1rongga.sch.id` | `maya` | Guru | 0 Soal | 🟢 **Terhubung** (`5955d317...794d`) |
| 33 | **NURAHMAN, S.Pd., ** | `-` | `nurahmanhasbullah@smkn1rongga.sch.id` | `nurahmanhasbullah` | Guru | 120 Soal | 🟢 **Terhubung** (`98605634...a012`) |
| 34 | **RAHMA INTAN PRATIWI, S.Pd., ** | `-` | `intan@smkn1rongga.sch.id` | `intan` | Guru | 124 Soal | 🟢 **Terhubung** (`39f69cf3...6aab`) |
| 35 | **REGINA ISHAURA, S.Pd** | `-` | `regina@smkn1rongga.sch.id` | `regina` | Guru | 77 Soal | 🟢 **Terhubung** (`296e28a8...04ec`) |
| 36 | **RIZAL FIRMANSYAH, S.Hut.,MP** | `-` | `rizalfirmansyah@smkn1rongga.sch.id` | `rizalfirmansyah` | Guru | 0 Soal | 🟢 **Terhubung** (`135125f2...5240`) |
| 37 | **RIZAL MARDIANA, S.Pd** | `-` | `rizalmardiana@smkn1rongga.sch.id` | `rizalmardiana` | Guru | 40 Soal | 🟢 **Terhubung** (`a0e4e41e...cf92`) |
| 38 | **SAEPUL ANWARULAH, S.Pd** | `-` | `saeful@smkn1rongga.sch.id` | `saeful` | Guru | 80 Soal | 🟢 **Terhubung** (`3c8537b7...bf66`) |
| 39 | **SANDI SAPRUDIN, S.Sn** | `-` | `sandi@smkn1rongga.sch.id` | `sandi` | Guru | 0 Soal | 🟢 **Terhubung** (`616a35b8...6979`) |
| 40 | **SETIA PERMANA,S.Pd., ** | `-` | `setiapermana@smkn1rongga.sch.id` | `setiapermana` | Guru | 11 Soal | 🟢 **Terhubung** (`2dbb38aa...afce`) |
| 41 | **SOPIYUDIN LATIF,S.T,  ** | `-` | `sopiyudinlatif22@smkn1rongga.sch.id` | `sopiyudinlatif22` | Guru | 105 Soal | 🟢 **Terhubung** (`b3adcdce...0c50`) |
| 42 | **WENDI ZULFIKAR FAIZ,S.Pd.I** | `-` | `wendizulfikar@smkn1rongga.sch.id` | `wendizulfikar` | Guru | 75 Soal | 🟢 **Terhubung** (`a501f121...8816`) |
| 43 | **Wawan Hidayat, S.Pd** | `-` | `wawanhidayat@smkn1rongga.sch.id` | `wawanhidayat` | Guru | 90 Soal | 🟢 **Terhubung** (`9a21ab5c...e8fb`) |
| 44 | **YANTI HERLANI, SP** | `-` | `yantiherlani@smkn1rongga.sch.id` | `yantiherlani` | Guru | 189 Soal | 🟢 **Terhubung** (`117c8a1e...2e71`) |
| 45 | **YOGA ASMARA, S.Pd** | `-` | `yogaasmara@smkn1rongga.sch.id` | `yogaasmara` | Guru | 80 Soal | 🟢 **Terhubung** (`a9b779b9...139c`) |
| 46 | **YULI ROMANSAH, S.Kom** | `-` | `yuroromansah@smkn1rongga.sch.id` | `yuroromansah` | Guru | 40 Soal | 🟢 **Terhubung** (`7b7ca494...8e62`) |
| 47 | **meta** | `-` | `meta@co` | `meta` | Guru | 0 Soal | 🟢 **Terhubung** (`43b7c02d...8371`) |