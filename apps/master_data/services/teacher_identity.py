"""Identitas guru: NIP dari data pusat dicocokkan ke guru Exam.

Username Keycloak guru adalah NIP, tetapi akun guru lama di Exam memakai nama pendek (misalnya
`gumelar`) dan hampir tidak menyimpan NIP. Pengisian awal NIP dilakukan lewat nama, hanya untuk
pasangan yang cocok tunggal dan persis; sisanya diserahkan ke admin.
"""
import re
from collections import defaultdict

# Gelar di depan nama; gelar di belakang sudah terbuang karena hanya bagian sebelum koma yang dipakai
PREFIX_TITLES = {'drs', 'dra', 'dr', 'h', 'hj', 'ir', 'prof', 'kh'}


def normalize_person_name(name):
    base = str(name or '').split(',')[0].lower()
    words = re.sub(r'[^a-z\s]', ' ', base.replace('.', '. ')).split()
    while words and words[0] in PREFIX_TITLES:
        words.pop(0)
    return ' '.join(words)


def match_staff_to_teachers(staff, teachers):
    """
    Pasangkan staf pusat (punya NIP) dengan guru Exam lewat nama yang dinormalkan.
    Hanya pasangan satu-lawan-satu yang diterima; nama yang muncul ganda di salah satu sisi dilewati.
    """
    exam_by_name = defaultdict(list)
    for teacher in teachers:
        exam_by_name[normalize_person_name(teacher.full_name)].append(teacher)

    staff_by_name = defaultdict(list)
    for s in staff:
        if s.get('nip'):
            staff_by_name[normalize_person_name(s.get('fullName') or s.get('full_name'))].append(s)

    matches, ambiguous, unmatched = [], [], []
    for name, rows in staff_by_name.items():
        label = rows[0].get('fullName') or rows[0].get('full_name')
        candidates = exam_by_name.get(name, [])
        if len(rows) == 1 and len(candidates) == 1:
            matches.append((candidates[0], str(rows[0]['nip']).strip()))
        elif candidates or len(rows) > 1:
            ambiguous.append(label)
        else:
            unmatched.append(label)
    return {'matches': matches, 'ambiguous': sorted(ambiguous), 'unmatched_staff': sorted(unmatched)}
