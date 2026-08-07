"use client";

import { useState, useEffect } from "react";
import { instructorAPI, CohortHeatmapResponse, CohortStudentRow, CohortTopicMeta } from "@/lib/api";
import InstructorRouteGuard from "@/components/instructor/InstructorRouteGuard";
import { Users, ArrowLeft } from "lucide-react";
import Link from "next/link";

// ── Helpers ────────────────────────────────────────────────────────────────────

function cellBg(value: number | null): string {
  if (value === null) return "#f3f4f6";
  const pct = Math.round(value * 100);
  if (pct >= 70) return `rgba(34,197,94,${0.15 + (pct - 70) / 30 * 0.5})`;
  if (pct >= 40) return `rgba(245,158,11,${0.15 + (pct - 40) / 30 * 0.4})`;
  return `rgba(239,68,68,${0.15 + (40 - pct) / 40 * 0.4})`;
}

// ── Heatmap Table ──────────────────────────────────────────────────────────────

function HeatmapTable({
  students,
  topics,
}: {
  students: CohortStudentRow[];
  topics: CohortTopicMeta[];
}) {
  const [sortKey, setSortKey] = useState<"name" | "avg">("avg");

  const sorted = [...students].sort((a, b) => {
    if (sortKey === "avg") {
      const av = a.avg_mastery ?? -1;
      const bv = b.avg_mastery ?? -1;
      return bv - av;
    }
    return a.display_name.localeCompare(b.display_name, "tr");
  });

  return (
    <div className="overflow-x-auto rounded-xl border shadow-sm">
      <table className="min-w-full text-xs border-collapse">
        <thead>
          <tr className="bg-gray-50 border-b">
            <th
              className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left font-semibold text-gray-700 cursor-pointer whitespace-nowrap"
              onClick={() => setSortKey("name")}
            >
              Öğrenci {sortKey === "name" ? "↑" : ""}
            </th>
            {topics.map((t) => (
              <th
                key={t.topic_id}
                className="px-2 py-2 font-medium text-gray-600 text-center whitespace-nowrap max-w-[80px]"
                title={t.label}
              >
                <div className="truncate max-w-[72px]">{t.label}</div>
                {t.cohort_avg !== null && (
                  <div className="text-[10px] text-gray-400 font-normal">
                    ort. {Math.round(t.cohort_avg * 100)}%
                  </div>
                )}
              </th>
            ))}
            <th
              className="px-3 py-2 font-semibold text-gray-700 cursor-pointer whitespace-nowrap"
              onClick={() => setSortKey("avg")}
            >
              Ort. {sortKey === "avg" ? "↓" : ""}
            </th>
            <th className="px-3 py-2 font-medium text-gray-600 whitespace-nowrap">
              Ustalaşılan
            </th>
          </tr>
          {/* Cohort avg row */}
          <tr className="bg-blue-50 border-b">
            <td className="sticky left-0 z-10 bg-blue-50 px-3 py-1.5 font-semibold text-blue-700">
              Kohort Ort.
            </td>
            {topics.map((t) => (
              <td
                key={t.topic_id}
                className="px-2 py-1.5 text-center font-medium"
                style={{ backgroundColor: cellBg(t.cohort_avg) }}
              >
                {t.cohort_avg !== null ? `${Math.round(t.cohort_avg * 100)}%` : "—"}
              </td>
            ))}
            <td className="px-3 py-1.5 text-center font-semibold text-blue-700">
              {students.length > 0
                ? `${Math.round(
                    (students.reduce((s, st) => s + (st.avg_mastery ?? 0), 0) /
                      students.filter((st) => st.avg_mastery !== null).length) *
                      100
                  )}%`
                : "—"}
            </td>
            <td className="px-3 py-1.5 text-center text-blue-700">—</td>
          </tr>
        </thead>
        <tbody>
          {sorted.map((student) => (
            <tr key={student.user_id} className="border-b hover:bg-gray-50 transition-colors">
              <td className="sticky left-0 z-10 bg-white hover:bg-gray-50 px-3 py-2 font-medium text-gray-800 whitespace-nowrap">
                <Link
                  href={`/instructor/students/${student.user_id}`}
                  className="hover:text-blue-600 hover:underline"
                >
                  {student.display_name}
                </Link>
              </td>
              {topics.map((t) => {
                const val = student.mastery[t.topic_id] ?? null;
                return (
                  <td
                    key={t.topic_id}
                    className="px-2 py-2 text-center font-medium"
                    style={{ backgroundColor: cellBg(val) }}
                    title={val !== null ? `${Math.round(val * 100)}%` : "Denenmedi"}
                  >
                    {val !== null ? `${Math.round(val * 100)}%` : "—"}
                  </td>
                );
              })}
              <td className="px-3 py-2 text-center font-semibold text-gray-700">
                {student.avg_mastery !== null
                  ? `${Math.round(student.avg_mastery * 100)}%`
                  : "—"}
              </td>
              <td className="px-3 py-2 text-center">
                <span
                  className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                    student.mastered_count > 0
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {student.mastered_count} / {topics.length}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

function CohortPageContent() {
  const [data, setData] = useState<CohortHeatmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    instructorAPI
      .getCohortMasteryHeatmap()
      .then(setData)
      .catch(() => setError("Veri yüklenemedi."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Link
              href="/instructor/dashboard"
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <ArrowLeft size={18} className="text-gray-600" />
            </Link>
            <div className="flex items-center gap-2">
              <Users size={22} className="text-blue-600" />
              <div>
                <h1 className="text-lg font-bold text-gray-900">Kohort Ustalık Isı Haritası</h1>
                <p className="text-xs text-gray-500">
                  Öğrenci × Konu BKT matrisi · %70 eşiği yeşil
                </p>
              </div>
            </div>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {data && (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-4 gap-3 mb-5">
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-gray-900">{data.n_students}</p>
                <p className="text-xs text-gray-500">Öğrenci</p>
              </div>
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-blue-600">{data.n_topics}</p>
                <p className="text-xs text-gray-500">Konu</p>
              </div>
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-green-600">
                  {data.students.filter(
                    (s) => s.avg_mastery !== null && s.avg_mastery >= data.mastery_threshold
                  ).length}
                </p>
                <p className="text-xs text-gray-500">Genel Ustalık Eşiği Aşan</p>
              </div>
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-orange-500">
                  {data.students.filter(
                    (s) => s.avg_mastery !== null && s.avg_mastery < 0.4
                  ).length}
                </p>
                <p className="text-xs text-gray-500">Risk Altında</p>
              </div>
            </div>

            {data.n_students === 0 ? (
              <div className="bg-white rounded-xl border p-10 text-center text-sm text-gray-500">
                <Users size={32} className="mx-auto mb-3 text-gray-300" />
                Henüz aktif öğrenci yok.
              </div>
            ) : (
              <HeatmapTable
                students={data.students}
                topics={data.topics}
              />
            )}

            <p className="text-[10px] text-gray-400 text-center mt-4">
              Hesaplanma: {new Date(data.computed_at).toLocaleString("tr-TR")} ·
              Eşik: %{Math.round(data.mastery_threshold * 100)} · — = henüz denenmedi
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default function CohortPage() {
  return (
    <InstructorRouteGuard>
      <CohortPageContent />
    </InstructorRouteGuard>
  );
}
