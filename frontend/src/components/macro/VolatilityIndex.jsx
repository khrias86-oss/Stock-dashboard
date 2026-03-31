"use client";

/**
 * 그래프 2: 시장 변동성 및 지수 바닥 확인
 * -- VIX 빨간 실선 + S&P500/KOSPI 오버레이
 * -- VIX 구간별 배경 음영 (안일/정상/경계/공포/극단공포)
 * -- VIX ≥ 30 시점: 🚨 글로우 점 + 수직선
 */

import useSWR from "swr";
import {
  ComposedChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Label,
} from "recharts";
import ChartCard from "../common/ChartCard";
import { fetcher, swrOptions } from "../../hooks/useApi";

/*
 * VIX 해석 구간 (CBOE 표준 + 시장 관행)
 * - 0~15:  안일/탐욕 — 시장 과열 경고
 * - 15~20: 정상 — 기본 변동성
 * - 20~30: 경계 — 불확실성 상승
 * - 30~40: 공포 — 시장 스트레스
 * - 40+:   극단 공포 — 패닉, 역발상 매수 기회
 */
const VIX_ZONES = [
  { y1: 0,  y2: 15, fill: "hsla(150, 60%, 40%, 0.06)", label: "안일" },
  { y1: 15, y2: 20, fill: "hsla(210, 50%, 50%, 0.04)", label: "정상" },
  { y1: 20, y2: 30, fill: "hsla(40, 70%, 50%, 0.06)", label: "경계" },
  { y1: 30, y2: 40, fill: "hsla(0, 60%, 50%, 0.08)", label: "공포" },
  { y1: 40, y2: 80, fill: "hsla(0, 80%, 40%, 0.12)", label: "극단공포" },
];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  /* VIX 값에 따라 구간 라벨 추가 */
  const vixEntry = payload.find((p) => p.dataKey === "vix");
  const vixVal = vixEntry?.value;
  let vixZone = "";
  if (vixVal != null) {
    if (vixVal >= 40) vixZone = "🔴 극단 공포";
    else if (vixVal >= 30) vixZone = "🟠 공포";
    else if (vixVal >= 20) vixZone = "🟡 경계";
    else if (vixVal >= 15) vixZone = "🟢 정상";
    else vixZone = "⚪ 안일 (과열 주의)";
  }

  return (
    <div
      style={{
        background: "hsl(225, 20%, 11%)",
        border: "1px solid hsla(220, 15%, 30%, 0.5)",
        borderRadius: "8px",
        padding: "10px 14px",
        fontSize: "0.75rem",
        lineHeight: "1.8",
        boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
      }}
    >
      <p style={{ color: "hsl(220, 15%, 92%)", fontWeight: 600, marginBottom: 4 }}>{label}</p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color }}>
          {entry.name}: {entry.value != null ? Number(entry.value).toLocaleString("ko-KR", { maximumFractionDigits: 2 }) : "N/A"}
        </p>
      ))}
      {vixZone && (
        <p style={{ color: "hsl(220, 10%, 55%)", marginTop: 4, borderTop: "1px solid hsla(220,15%,25%,0.3)", paddingTop: 4 }}>
          시장 상태: {vixZone}
        </p>
      )}
    </div>
  );
}

/* VIX 값에 따른 색상 반환 (초록 → 노랑 → 빨강) */
function getVixColor(vix) {
  if (vix >= 40) return "hsl(0, 90%, 45%)";   // 극단 공포 - 진한 빨강
  if (vix >= 30) return "hsl(0, 80%, 55%)";   // 공포 - 빨강
  if (vix >= 25) return "hsl(15, 85%, 55%)";  // 높은 경계 - 오렌지레드
  if (vix >= 20) return "hsl(35, 90%, 55%)";  // 경계 - 오렌지
  if (vix >= 15) return "hsl(50, 90%, 55%)";  // 정상 - 노랑
  if (vix >= 12) return "hsl(80, 70%, 50%)";  // 낮은 정상 - 연두
  return "hsl(150, 70%, 50%)";                // 안일 - 초록
}

/* VIX 30 이상인 데이터에 글로우 점 렌더링 */
function VixAlertDot(props) {
  const { cx, cy, payload } = props;
  if (payload?.vix >= 30) {
    const color = getVixColor(payload.vix);
    return (
      <g>
        <circle cx={cx} cy={cy} r={6} fill={`${color}44`} />
        <circle cx={cx} cy={cy} r={3} fill={color} />
      </g>
    );
  }
  return null;
}

/* X축 월초(1일) 필터링 */
function monthStartTickFormatter(dateStr) {
  if (!dateStr) return "";
  const d = dateStr.split("-");
  if (d[2] === "01" || d[2] === "02" || d[2] === "03") {
    return `${d[0].slice(2)}.${d[1]}`;
  }
  return "";
}

function isMonthStart(dateStr) {
  if (!dateStr) return false;
  const day = parseInt(dateStr.split("-")[2], 10);
  return day <= 3;
}

export default function VolatilityIndex({ aiComment, signals: externalSignals }) {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/macro/volatility",
    fetcher,
    swrOptions
  );

  const hasData = data?.series?.length > 0;

  /* 최신 VIX 값 기준 시그널 */
  const getSignalBadge = () => {
    if (!hasData) return null;
    const latest = data.series[data.series.length - 1];
    const vix = latest?.vix;
    if (vix == null) return null;
    if (vix >= 40) return <span className="signal-badge danger">🚨 극단공포 VIX {vix.toFixed(1)}</span>;
    if (vix >= 30) return <span className="signal-badge danger">🔴 공포 VIX {vix.toFixed(1)}</span>;
    if (vix >= 20) return <span className="signal-badge warning">🟡 경계 VIX {vix.toFixed(1)}</span>;
    if (vix >= 15) return <span className="signal-badge safe">🟢 정상 VIX {vix.toFixed(1)}</span>;
    return <span className="signal-badge strong">⚪ 안일 VIX {vix.toFixed(1)}</span>;
  };

  /* X축에서 월초만 틱으로 표시 */
  const monthTicks = hasData
    ? data.series.filter((d) => isMonthStart(d.date)).map((d) => d.date)
    : [];

  return (
    <ChartCard
      title="시장 변동성 & 지수 바닥 확인"
      icon="🌊"
      description="VIX 구간: 0~15 안일(과열) | 15~20 정상 | 20~30 경계 | 30+ 공포(역발상 매수 기회)"
      badge={getSignalBadge()}
      isLoading={isLoading}
      error={error}
      onRetry={() => mutate()}
      aiComment={aiComment}
      signals={externalSignals}
    >
      {hasData && (
        <>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={data.series} margin={{ top: 10, right: 70, bottom: 5, left: 20 }}>
              {/* VIX 구간별 배경 음영 */}
              {VIX_ZONES.map((zone, i) => (
                <ReferenceArea
                  key={i}
                  yAxisId="vix"
                  y1={zone.y1}
                  y2={zone.y2}
                  fill={zone.fill}
                  strokeOpacity={0}
                />
              ))}

              <XAxis
                dataKey="date"
                ticks={monthTicks}
                tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: "hsla(220, 15%, 25%, 0.3)" }}
                tickFormatter={(v) => {
                  const d = v.split("-");
                  return `${d[0].slice(2)}.${d[1]}`;
                }}
              />
              <YAxis
                yAxisId="vix"
                tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                domain={[0, "auto"]}
              >
                <Label
                  value="VIX 지수"
                  angle={-90}
                  position="insideLeft"
                  offset={-5}
                  style={{ fill: "hsl(0, 80%, 60%)", fontSize: 11, fontWeight: 600 }}
                />
              </YAxis>
              <YAxis
                yAxisId="index"
                orientation="right"
                tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                domain={[0, 10000]}
              >
                <Label
                  value="지수 (S&P500 / KOSPI)"
                  angle={90}
                  position="insideRight"
                  offset={-5}
                  style={{ fill: "hsl(210, 70%, 55%)", fontSize: 11, fontWeight: 600 }}
                />
              </YAxis>
              <Tooltip content={<CustomTooltip />} />

              {/* VIX 임계선들 */}
              <ReferenceLine yAxisId="vix" y={15} stroke="hsla(150, 50%, 50%, 0.3)" strokeDasharray="4 4" />
              <ReferenceLine yAxisId="vix" y={20} stroke="hsla(40, 60%, 50%, 0.3)" strokeDasharray="4 4" />
              <ReferenceLine
                yAxisId="vix"
                y={30}
                stroke="hsla(0, 80%, 55%, 0.5)"
                strokeDasharray="6 3"
                label={{
                  value: "공포 (30)",
                  position: "insideTopLeft",
                  fill: "hsl(0, 80%, 55%)",
                  fontSize: 10,
                }}
              />
              <ReferenceLine yAxisId="vix" y={40} stroke="hsla(0, 90%, 45%, 0.5)" strokeDasharray="6 3" />

              {/* VIX 30 이상 날짜에 수직선 */}
              {(data.alert_dates || []).slice(0, 10).map((date, i) => (
                <ReferenceLine
                  key={i}
                  x={date}
                  yAxisId="vix"
                  stroke="hsla(0, 80%, 55%, 0.15)"
                  strokeDasharray="2 4"
                />
              ))}

              {/* VIX 그라데이션 정의: 초록(낮음) → 노랑(경계) → 빨강(공포) */}
              <defs>
                <linearGradient id="vixLineGradient" x1="0" y1="1" x2="0" y2="0">
                  {/* y2=0은 차트 상단(높은 VIX), y1=1은 차트 하단(낮은 VIX) */}
                  <stop offset="0%" stopColor="hsl(150, 70%, 50%)" stopOpacity={1} />
                  <stop offset="25%" stopColor="hsl(120, 60%, 50%)" stopOpacity={1} />
                  <stop offset="40%" stopColor="hsl(50, 90%, 55%)" stopOpacity={1} />
                  <stop offset="60%" stopColor="hsl(30, 90%, 55%)" stopOpacity={1} />
                  <stop offset="75%" stopColor="hsl(0, 80%, 55%)" stopOpacity={1} />
                  <stop offset="100%" stopColor="hsl(0, 90%, 40%)" stopOpacity={1} />
                </linearGradient>
                <linearGradient id="vixFillGradient" x1="0" y1="1" x2="0" y2="0">
                  <stop offset="0%" stopColor="hsl(150, 70%, 50%)" stopOpacity={0.02} />
                  <stop offset="40%" stopColor="hsl(50, 90%, 55%)" stopOpacity={0.04} />
                  <stop offset="75%" stopColor="hsl(0, 80%, 55%)" stopOpacity={0.08} />
                  <stop offset="100%" stopColor="hsl(0, 90%, 40%)" stopOpacity={0.15} />
                </linearGradient>
              </defs>

              {/* VIX — 값 기반 그라데이션 (초록→노랑→빨강) */}
              <Area
                yAxisId="vix"
                type="monotone"
                dataKey="vix"
                name="VIX"
                stroke="url(#vixLineGradient)"
                fill="url(#vixFillGradient)"
                strokeWidth={2.5}
                dot={<VixAlertDot />}
                activeDot={{ r: 5 }}
              />

              {/* S&P500 */}
              <Line
                yAxisId="index"
                type="monotone"
                dataKey="sp500"
                name="S&P 500"
                stroke="hsl(210, 90%, 60%)"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
              />

              {/* KOSPI */}
              <Line
                yAxisId="index"
                type="monotone"
                dataKey="kospi"
                name="KOSPI"
                stroke="hsl(150, 70%, 50%)"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
              />

              {/* KOSPI 거래량 */}
              <Bar
                yAxisId="index"
                dataKey="kospi_volume"
                name="KOSPI 거래량"
                fill="hsla(150, 60%, 50%, 0.15)"
                radius={[2, 2, 0, 0]}
              />
            </ComposedChart>
          </ResponsiveContainer>

          <div className="chart-legend">
            <div className="legend-item">
              <span style={{
                width: "40px", height: "8px", borderRadius: "4px", display: "inline-block",
                background: "linear-gradient(90deg, hsl(150,70%,50%), hsl(50,90%,55%), hsl(0,80%,55%))"
              }} />
              VIX (초록=안일 → 빨강=공포)
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ background: "hsl(210, 90%, 60%)" }} />
              S&P 500
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ background: "hsl(150, 70%, 50%)" }} />
              KOSPI
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ background: "hsla(150, 60%, 50%, 0.4)" }} />
              KOSPI 거래량
            </div>
            <div className="legend-item" style={{ marginLeft: "auto", fontSize: "0.7rem", color: "var(--text-tertiary)" }}>
              배경: 안일 → 정상 → 경계 → 공포 → 극단공포
            </div>
          </div>
          <div className="chart-guide">
            <p><strong>📘 지표 해설</strong></p>
            <p>• <b>VIX (CBOE 변동성 지수)</b>: S&P500 옵션 가격에서 산출한 30일 예상 변동성. 시장의 &quot;공포 온도계&quot;.</p>
            <p>• <b>0~15 (안일)</b>: 투자자 과신 상태, 시장 과열 경고. 역발상으로 하락 대비 필요.</p>
            <p>• <b>15~20 (정상)</b>: 일반적 변동성 수준. 안정적 투자 환경.</p>
            <p>• <b>20~30 (경계)</b>: 불확실성 상승 중. 포지션 축소 검토.</p>
            <p>• <b>30+ (공포)</b>: 시장 스트레스 극심. 역사적으로 30 이상은 6~12개월 후 반등 확률 높음. 역발상 매수 검토.</p>
            <p>• <b>40+ (극단공포)</b>: 패닉 매도 수준. 주요 바닥 형성 구간.</p>
            <p style={{color: "var(--text-tertiary)", marginTop: "4px"}}>🔴 차트의 빨간 글로우 점 = VIX 30 이상 시점. S&P500/KOSPI와 역상관 관계 확인.</p>
          </div>
        </>
      )}
    </ChartCard>
  );
}
