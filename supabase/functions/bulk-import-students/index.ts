import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // 1. Handle Preflight Request untuk CORS (Biar nggak error pas dipanggil dari browser)
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // 2. Setup Kunci Master (Service Role) - Mengambil dari environment Supabase
    const supabaseAdmin = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const { students } = await req.json() // Menerima data JSON dari React
    const results = []

    for (const student of students) {
      const dummyEmail = `${student.NIS}@student.smkn1rongga.sch.id`

      // 3. Cari ID Kelas berdasarkan Nama Kelas (misal: "10 RPL 1")
      const { data: cls } = await supabaseAdmin
        .from('classes')
        .select('id')
        .eq('name', student.Kode_Kelas)
        .single()

      if (cls) {
        // 4. Buat Akun Auth (Bypass Email Rate Limit & Auto Confirm)
        const { data: authUser, error: authError } = await supabaseAdmin.auth.admin.createUser({
          email: dummyEmail,
          password: "smk" + student.NIS,
          email_confirm: true, // Akun langsung aktif tanpa verifikasi email
          user_metadata: { role: 'siswa' }
        })

        if (!authError && authUser.user) {
          // 5. Masukkan ke Tabel Profil Students
          const { error: insertError } = await supabaseAdmin.from('students').insert({
            user_id: authUser.user.id,
            nis: student.NIS,
            full_name: student.Nama_Lengkap,
            class_id: cls.id,
            status: 'aktif'
          })
          
          if (!insertError) results.push({ nis: student.NIS, status: 'success' })
        } else {
          results.push({ nis: student.NIS, status: 'failed', error: authError?.message })
        }
      }
    }

    return new Response(
      JSON.stringify({ message: "Proses Selesai", detail: results }), 
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    )
  } catch (err) {
    return new Response(
      JSON.stringify({ error: err.message }), 
      { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    )
  }
})