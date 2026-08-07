"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import {
  analyticsAPI,
  MasteryTrajectoryResponse,
  TopicTrajectory,
  LearningCurveResponse,
  LearningCurveTopic,
} from "@/lib/api";
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
  ComposedChart,
  Scatter,
} from "recharts";
import { TrendingUp, ArrowLeft, Brain, ChevronDown, Activity } from "lucide-react";

// ── Helpers ────────────────────────────────────────────────────────────────────

function masteryColor(p: number): string {
  if (p >= 0.7) return "#22c55e";
  if (p >= 0.4) return "#f59e0b";
  return "#ef4444";
}

function masteryLabel(p: number): string {
  if (p >= 0.7) return "Ustalaşıldı";
  if (p >= 0.4) return "Gelişiyor";
  return "Başlangıç";
}

// ── Mastery Trajectory Chart ───────────────────────────────────────────────────

function TrajectoryChart({ topic }: { topic: TopicTrajectory }) {
  const data = topic.points.map((pt) => ({
    n: pt.n,
    mastery: Math.round(pt.mastery * 100),
    ci_lower: Math.round(pt.ci_lower * 100),
    ci_upper: Math.round(pt.ci_upper * 100),
    correct: pt.correct,
  }));

  const color = masteryColor(topic.current_mastery);

  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-gray-800">{topic.label}</h3>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {masteryLabel(topic.current_mastery)} — {Math.round(topic.current_mastery * 100)}%
        </span>
      </div>
      <p className="text-xs text-gray-400 mb-3">
        {topic.n_observations} gözlem · 95% güven bantlı BKT yörüngesi
      </p>

      {data.length === 0 ? (
        <div className="h-32 flex items-center justify-center text-xs text-gray-400">
          Henüz yeterli veri yok
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id={`ci-${topic.topic_id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.15} />
                <stop offset="95%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="n"
              tick={{ fontSize: 11 }}
              label={{ value: "Gözlem #", position: "insideBottomRight", offset: -4, fontSize: 10 }}
            />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
            <Tooltip
              formatter={(value, name) => {
                const label =
                  name === "mastery" ? "P(L_n)" :
                  name === "ci_upper" ? "CI Üst" :
                  name === "ci_lower" ? "CI Alt" : String(name);
                return [`${value}%`, label] as [string, string];
              }}
            />
            <ReferenceLine y={70} stroke="#22c55e" strokeDasharray="4 2" strokeWidth={1} />
            <Area type="monotone" dataKey="ci_upper" stroke="none" fill={`url(#ci-${topic.topic_id})`} />
            <Area type="monotone" dataKey="ci_lower" stroke="none" fill="white" />
            <Line
              type="monotone"
              dataKey="mastery"
              stroke={color}
              strokeWidth={2}
              dot={(props) => {
                const { cx, cy, payload } = props;
                return (
                  <circle
                    key={`dot-${payload.n}`}
                    cx={cx}
                    cy={cy}
                    r={4}
                    fill={payload.correct ? color : "#ef4444"}
                    stroke="white"
                    strokeWidth={1.5}
                  />
                );
              }}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
      <p className="text-[10px] text-gray-400 mt-2">
        Yeşil nokta = doğru · Kırmızı nokta = yanlış · Kesik çizgi = %70 ustalık eşiği
      </p>
    </div>
  );
}

// ── Learning Curve Chart ───────────────────────────────────────────────────────

function LearningCurveChart({ topic }: { topic: LearningCurveTopic }) {
  const { fit, observed_accuracy, n_observations } = topic;
  const currentN = n_observations;

  const modelLabel =
    fit.model === "exponential" ? "Üstel Doyum" :
    fit.model === "power_law" ? "Güç Yasası" : null;

  // Merge observed and fitted into one series keyed by n
  const fitMap = new Map(fit.fitted_curve.map((p) => [p.n, p.predicted]));
  const obsMap = new Map(observed_accuracy.map((p) => [p.n, p.cumulative_accuracy]));

  const allNs = Array.from(
    new Set([...fitMap.keys(), ...obsMap.keys()])
  ).sort((a, b) => a - b);

  const data = allNs.map((n) => ({
    n,
    observed: obsMap.has(n) ? Math.round((obsMap.get(n)! * 100) * 10) / 10 : undefined,
    fitted: fitMap.has(n) ? Math.round((fitMap.get(n)! * 100) * 10) / 10 : undefined,
    isProjection: n > currentN,
  }));

  const proj = fit.projected_trials_to_mastery;

  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-gray-800">{topic.label}</h3>
        {modelLabel && fit.r_squared !== null && (
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {modelLabel} · R²={fit.r_squared.toFixed(2)}
          </span>
        )}
      </div>

      {fit.note && (
        <p className="text-xs text-gray-400 mb-3 italic">{fit.note}</p>
      )}

      {proj !== null && proj !== undefined ? (
        <p className="text-xs text-blue-600 mb-3">
          Tahmini ustalık: <strong>{proj}. deneme</strong> sonrası
          {proj > currentN ? ` (${proj - currentN} deneme kaldı)` : " ✓ ulaşıldı"}
        </p>
      ) : fit.model && (
        <p className="text-xs text-gray-400 mb-3">
          Mevcut eğimle ustalık eşiğine ulaşma öngörülemiyor
        </p>
      )}

      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="n"
            tick={{ fontSize: 11 }}
            label={{ value: "Deneme #", position: "insideBottomRight", offset: -4, fontSize: 10 }}
          />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
          <Tooltip
            formatter={(value, name) => {
              const label = name === "observed" ? "Kümülatif Doğruluk" : "Tahmin";
              return [`${value}%`, label] as [string, string];
            }}
          />
          <ReferenceLine y={70} stroke="#22c55e" strokeDasharray="4 2" strokeWidth={1} />
          {proj && <ReferenceLine x={proj} stroke="#3b82f6" strokeDasharray="4 2" strokeWidth={1} />}
          {/* Observed dots */}
          <Scatter dataKey="observed" fill="#6366f1" r={4} />
          {/* Fitted line */}
          <Line
            type="monotone"
            dataKey="fitted"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            strokeDasharray="0"
          />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="text-[10px] text-gray-400 mt-2">
        Mor noktalar = gözlem · Mavi çizgi = model · Kesik çizgi = projeksiyon / %70 eşik
      </p>
    </div>
  );
}

// ── Topic Summary Row ──────────────────────────────────────────────────────────

function TopicSummaryRow({
  topic,
  selected,
  onClick,
}: {
  topic: TopicTrajectory;
  selected: boolean;
  onClick: () => void;
}) {
  const color = masteryColor(topic.current_mastery);
  const pct = Math.round(topic.current_mastery * 100);
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left ${
        selected ? "border-blue-400 bg-blue-50" : "border-gray-200 bg-white hover:bg-gray-50"
      }`}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{topic.label}</p>
        <p className="text-xs text-gray-400">{topic.n_observations} gözlem</p>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
        </div>
        <span className="text-xs font-semibold w-10 text-right" style={{ color }}>
          {pct}%
        </span>
      </div>
      <ChevronDown
        size={14}
        className={`text-gray-400 transition-transform ${selected ? "rotate-180" : ""}`}
      />
    </button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "trajectory" | "learning-curve";

export default function AnalyticsPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>("trajectory");
  const [trajectory, setTrajectory] = useState<MasteryTrajectoryResponse | null>(null);
  const [learningCurve, setLearningCurve] = useState<LearningCurveResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      analyticsAPI.getMasteryTrajectory(),
      analyticsAPI.getLearningCurve(),
    ])
      .then(([traj, curve]) => {
        setTrajectory(traj);
        setLearningCurve(curve);
        if (traj.topics.length > 0) setSelectedTopic(traj.topics[0].topic_id);
      })
      .catch(() => setError("Veri yüklenemedi."))
      .finally(() => setLoading(false));
  }, [user]);

  const activeTrajectoryTopic =
    trajectory?.topics.find((t) => t.topic_id === selectedTopic) ?? null;
  const activeLearningTopic =
    learningCurve?.topics.find((t) => t.topic_id === selectedTopic) ?? null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft size={18} className="text-gray-600" />
          </button>
          <div className="flex items-center gap-2">
            <Brain size={22} className="text-blue-600" />
            <div>
              <h1 className="text-lg font-bold text-gray-900">Öğrenme Analitiği</h1>
              <p className="text-xs text-gray-500">
                BKT yörüngesi · Öğrenme eğrisi · Ustalık projeksiyonu
              </p>
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

        {trajectory && (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-gray-900">{trajectory.topics.length}</p>
                <p className="text-xs text-gray-500 mt-0.5">Konu</p>
              </div>
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-blue-600">
                  {trajectory.topics.reduce((s, t) => s + t.n_observations, 0)}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">Toplam Gözlem</p>
              </div>
              <div className="bg-white rounded-xl border p-4 shadow-sm text-center">
                <p className="text-2xl font-bold text-green-600">
                  {trajectory.topics.filter((t) => t.current_mastery >= 0.7).length}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">Ustalaşılan</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-5">
              <button
                onClick={() => setTab("trajectory")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-all ${
                  tab === "trajectory" ? "bg-white shadow-sm text-blue-600" : "text-gray-500"
                }`}
              >
                <Brain size={14} /> Ustalık Yörüngesi
              </button>
              <button
                onClick={() => setTab("learning-curve")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-all ${
                  tab === "learning-curve" ? "bg-white shadow-sm text-blue-600" : "text-gray-500"
                }`}
              >
                <Activity size={14} /> Öğrenme Eğrisi
              </button>
            </div>

            {trajectory.topics.length === 0 ? (
              <div className="bg-white rounded-xl border p-10 text-center text-sm text-gray-500">
                <TrendingUp size={32} className="mx-auto mb-3 text-gray-300" />
                Henüz analiz edilebilecek kadar veri yok.
              </div>
            ) : (
              <div className="space-y-3">
                {/* Active chart */}
                {tab === "trajectory" && activeTrajectoryTopic && (
                  <TrajectoryChart topic={activeTrajectoryTopic} />
                )}
                {tab === "learning-curve" && activeLearningTopic && (
                  <LearningCurveChart topic={activeLearningTopic} />
                )}

                {/* Topic list */}
                <div className="space-y-2 mt-4">
                  {trajectory.topics.map((t) => (
                    <TopicSummaryRow
                      key={t.topic_id}
                      topic={t}
                      selected={selectedTopic === t.topic_id}
                      onClick={() =>
                        setSelectedTopic(selectedTopic === t.topic_id ? null : t.topic_id)
                      }
                    />
                  ))}
                </div>
              </div>
            )}

            <p className="text-[10px] text-gray-400 text-center mt-6">
              Hesaplanma: {new Date(trajectory.computed_at).toLocaleString("tr-TR")}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
