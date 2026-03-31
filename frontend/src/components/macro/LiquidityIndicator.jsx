"use client";

/**
 * 그래프 3: 유동성 지표
 * -- M2 YoY 증감률 (좌측 Y축) + KOSPI/S&P500 (우측 Y축)
 * -- 유동성 변곡점(축소→확대, 확대→축소)을 화살표로 표시
 */

import useSWR from "swr";
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Label,
} from "recharts";
import ChartCard from "../common/ChartCard";
import { fetcher, swrOptions } from "../../hooks/useApi";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "hsl(225, 20%, 11%)", border: "1px solid hsla(220, 15%, 30%, 0.5)",
      borderRadius: "8px", padding: "10px 14px", fontSize: "0.75rem", lineHeight: "1.6",
      boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
    }}>
      <p style={{ color: "hsl(220, 15%, 92%)", fontWeight: 600, marginBottom: 4 }}>{label}</p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color }}>
          {entry.name}: {entry.value != null ? Number(entry.value).toLocaleString("ko-KR", { maximumFractionDigits: 2 }) : "N/A"}
          {entry.name.includes("M2") ? "%" : ""}
        </p>
      ))}
    </div>
  );
}

function InflectionDot(props) {
  const { cx, cy, payload, inflectionDates } = props;
  if (!inflectionDates || !payload) return null;
  const match = inflectionDates.find((p) => p.date === payload.date);
  if (!match) return null;
  const isExpanding = match.direction === "확대";
  const color = isExpanding ? "hsl(150, 70%, 50%)" : "hsl(0, 80%, 60%)";
  const arrow = isExpanding ? "▲" : "▼";
  return (
    <g>
      <circle cx={cx} cy={cy} r={8} fill={`${color}33`} />
      <circle cx={cx} cy={cy} r={4} fill={color} />
      <text x={cx} y={cy - 16} textAnchor="middle" fill={color} fontSize={12} fontWeight="bold">{arrow}</text>
      <text x={cx} y={cy - 28} textAnchor="middle" fill={color} fontSize={9}>유동성 {match.direction}</text>
    </g>
  );
}

function isMonthStart(dateStr) {
  if (!dateStr) return false;
  return parseInt(dateStr.split("-")[2], 10) <= 3;
}

export default function LiquidityIndicator({ aiComment, signals: externalSignals }) {
  const { data, error, isLoading, mutate } = useSWR("/api/macro/liquidity", fetcher, swrOptions);
  const hasData = data?.series?.length > 0;

  const getSignalBadge = () => {
    if (!hasData) return null;
    const latest = data.series[data.series.length - 1];
    const m2 = latest?.m2_us_yoy;
    if (m2 == null) return null;
    if (m2 < 0) return <span className="signal-badge danger">유동성 축소</span>;
    if (m2 < 3) return <span className="signal-badge warning">유동성 둔화</span>;
    return <span className="signal-badge safe">유동성 확대</span>;
  };

  const monthTicks = hasData ? data.series.filter((d) => isMonthStart(d.date)).map((d) => d.date) : [];

  return (
    <ChartCard title="유동성 지표 (M2 통화량)" icon="💧"
      description="M2 전년 동월 대비 증감률과 주요 지수 비교" badge={getSignalBadge()}
      isLoading={isLoading} error={error} onRetry={() => mutate()}
      aiComment={aiComment} signals={externalSignals}>
      {hasData && (
        <>
          {!data.has_m2_data && (
            <div style={{ background: "hsla(40, 90%, 55%, 0.08)", border: "1px solid hsla(40, 90%, 55%, 0.2)",
              borderRadius: "6px", padding: "8px 12px", marginBottom: "12px", fontSize: "0.75rem", color: "hsl(40, 95%, 55%)" }}>
              ⚠️ M2 데이터는 시뮬레이션입니다. FRED API Key 설정 시 실제 데이터로 전환됩니다.
            </div>
          )}
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={data.series} margin={{ top: 30, right: 70, bottom: 5, left: 20 }}>
              <XAxis dataKey="date" ticks={monthTicks} tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }}
                tickLine={false} axisLine={{ stroke: "hsla(220, 15%, 25%, 0.3)" }}
                tickFormatter={(v) => { const d = v.split("-"); return `${d[0].slice(2)}.${d[1]}`; }} />
              <YAxis yAxisId="m2" tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={(v) => `${v.toFixed(0)}%`}>
                <Label value="M2 YoY (%)" angle={-90} position="insideLeft" offset={-5}
                  style={{ fill: "hsl(35, 95%, 60%)", fontSize: 11, fontWeight: 600 }} />
              </YAxis>
              <YAxis yAxisId="index" orientation="right" tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }} tickLine={false} axisLine={false} domain={[0, 10000]}>
                <Label value="지수 (S&P500 / KOSPI)" angle={90} position="insideRight" offset={-5}
                  style={{ fill: "hsl(210, 70%, 55%)", fontSize: 11, fontWeight: 600 }} />
              </YAxis>
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine yAxisId="m2" y={0} stroke="hsla(220, 15%, 40%, 0.4)" strokeDasharray="4 4" />
              <Area yAxisId="m2" type="monotone" dataKey="m2_us_yoy" name="M2 미국 YoY" stroke="hsl(35, 95%, 60%)"
                fill="hsla(35, 90%, 55%, 0.08)" strokeWidth={2}
                dot={(props) => <InflectionDot {...props} inflectionDates={data.inflection_points} />} activeDot={{ r: 4 }} />
              <Line yAxisId="m2" type="monotone" dataKey="m2_kr_yoy" name="M2 한국 YoY" stroke="hsl(180, 60%, 55%)"
                strokeWidth={1.5} strokeDasharray="4 2" dot={false} activeDot={{ r: 3 }} />
              <Line yAxisId="index" type="monotone" dataKey="sp500" name="S&P 500" stroke="hsl(210, 90%, 60%)"
                strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} />
              <Line yAxisId="index" type="monotone" dataKey="kospi" name="KOSPI" stroke="hsl(150, 70%, 50%)"
                strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(35, 95%, 60%)" }} />M2 미국 YoY%</div>
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(180, 60%, 55%)" }} />M2 한국 YoY%</div>
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(210, 90%, 60%)" }} />S&P 500</div>
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(150, 70%, 50%)" }} />KOSPI</div>
          </div>
          <div className="chart-guide">
            <p><strong>📘 지표 해설</strong></p>
            <p>• <b>M2 통화량 YoY</b>: 전년 동월 대비 광의통화(M2) 증감률. 시중에 풀린 돈의 증가 속도를 측정합니다.</p>
            <p>• <b>양수 (+)</b>: 유동성 확대 중 → 자산 가격 상승에 우호적. 5% 이상이면 &quot;유동성 풍부&quot;.</p>
            <p>• <b>0% 근접</b>: 유동성 둔화 → 주식시장 상승 동력 약화. 보수적 대응 필요.</p>
            <p>• <b>음수 (-)</b>: 유동성 축소(긴축) → 자산 가격 하방 압력. 2022년 하락장도 M2 음전환 후 발생.</p>
            <p>• <b>▲/▼ 마커</b>: M2가 부호가 바뀌는 변곡점. 유동성 사이클 전환의 핵심 시점입니다.</p>
            <p style={{color: "var(--text-tertiary)", marginTop: "4px"}}>핵심: 지수는 유동성을 6~9개월 후행합니다. M2 확대 시작 → 6개월 후 주가 반등 패턴 확인.</p>
          </div>
        </>
      )}
    </ChartCard>
  );
}
