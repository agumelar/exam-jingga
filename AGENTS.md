<!-- context7 -->
Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service -- even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Use even when you think you know the answer -- your training data may not reflect recent changes. Prefer this over web search for library docs.

Do not use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Steps

1. Always start with `resolve-library-id` using the library name and the user's question, unless the user provides an exact library ID in `/org/project` format
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries (e.g., "next.js" not "nextjs", or rephrase the question). Use version-specific IDs when the user mentions a version
3. `query-docs` with the selected library ID and the user's full question (not single words)
4. Answer using the fetched docs
<!-- context7 -->

---

# 📌 SOP & ATURAN WAJIB PENGEMBANGAN EXAM JINGGA (USER RULES)

## 1. Mode Brainstorming vs Mode Eksekusi
* **Mode Brainstorming (Default)**: Setiap instruksi/pertanyaan dari user yang **TIDAK** mengandung kata **"proses"** atau **"eksekusi"** berarti murni fase **Diskusi, Analisis, dan Brainstorming**.
  * Dilarang keras melakukan modifikasi file, query insert/update/delete database, git commit, atau deploy ke server.
  * Jawaban fokus pada pemaparan analisis, penyebab, arsitektur, dan opsi solusi.
* **Mode Eksekusi**: Hanya aktif jika user memberikan kata kunci eksplisit **"proses"** atau **"eksekusi"**.

## 2. Alur Eksekusi Resmi (Workflow Deployment)
Setiap kali user memerintahkan **"proses"** atau **"eksekusi"**, alur kerja yang wajib dijalankan adalah:
1. **Implementasi & Verifikasi Kode Lokal**: Lakukan coding / perubahan file dan pastikan build frontend lulus (`npm run build`).
2. **Git Commit & Push ke GitHub**: Lakukan commit dengan pesan yang deskriptif dan push ke repository GitHub.
3. **Deploy & Reload di VPS**: Kirim update ke server VPS (`145.241.157.243` / `/opt/exam-jingga`), lakukan build di VPS, dan reload Nginx/service terkait.
4. **Dokumentasi Otomatis**: Perbarui file [`HANDOFF.md`](./HANDOFF.md) dan [`log.md`](./log.md).
