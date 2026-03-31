"use client";

/**
 * 그래프 4: 경기 선행 지표 (장단기 금리차)
 * -- 10Y - 2Y 금리차 Area 차트
 * -- 0 이하 역전 구간: 붉은 음영 처리
 * -- 역전→정상화 시점: '경기 침체 진입 주의' 강제 라벨
 */

import useSWR from "swr";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, ReferenceArea, ResponsiveContainer, Label,
} from "recharts";
import ChartCard from "../common/ChartCard";
import { fetcher, swrOptions } from "../../hooks/useApi";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const spread = payload.find((p) => p.dataKey === "spread");
  return (
    <div style={{
      background: "hsl(225, 20%, 11%)", border: "1px solid hsla(220, 15%, 30%, 0.5)",
      borderRadius: "8px", padding: "10px 14px", fontSize: "0.75rem", lineHeight: "1.6",
      boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
    }}>
      <p style={{ color: "hsl(220, 15%, 92%)", fontWeight: 600, marginBottom: 4 }}>{label}</p>
      {spread && (
        <p style={{ color: spread.value < 0 ? "hsl(0, 80%, 60%)" : "hsl(210, 90%, 60%)" }}>
          10Y-2Y 금리차: {spread.value != null ? spread.value.toFixed(3) : "N/A"}%
        </p>
      )}
      {payload.find((p) => p.dataKey === "yield_10y") && (
        <p style={{ color: "hsl(220, 10%, 55%)" }}>
          10Y: {payload.find((p) => p.dataKey === "yield_10y")?.value?.toFixed(3)}% |
          2Y: {payload.find((p) => p.dataKey === "yield_2y")?.value?.toFixed(3)}%
        </p>
      )}
    </div>
  );
}

function isMonthStart(dateStr) {
  if (!dateStr) return false;
  return parseInt(dateStr.split("-")[2], 10) <= 3;
}

export default function LeadingIndicator({ aiComment, signals: externalSignals }) {
  const { data, error, isLoading, mutate } = useSWR("/api/macro/leading-indicator", fetcher, swrOptions);
  const hasData = data?.series?.length > 0;

  const getSignalBadge = () => {
    if (!hasData) return null;
    const latest = data.series[data.series.length - 1];
    const spread = latest?.spread;
    if (spread == null) return null;
    if (spread < 0) return <span className="signal-badge danger">🔻 금리 역전</span>;
    if (spread < 0.5) return <span className="signal-badge warning">⚠️ 역전 근접</span>;
    return <span className="signal-badge safe">정상</span>;
  };

  const monthTicks = hasData ? data.series.filter((d) => isMonthStart(d.date)).map((d) => d.date) : [];

  return (
    <ChartCard title="경기 선행 지표 (장단기 금리차)" icon="📐"
      description="10년물 - 2년물 금리차 | 역전 구간은 경기 침체 선행 시그널"
      badge={getSignalBadge()} isLoading={isLoading} error={error} onRetry={() => mutate()}
      aiComment={aiComment} signals={externalSignals}>
      {hasData && (
        <>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={data.series} margin={{ top: 10, right: 30, bottom: 5, left: 20 }}>
              {(data.inversion_zones || []).map((zone, i) => (
                <ReferenceArea key={i} x1={zone.start} x2={zone.end} fill="hsla(0, 60%, 50%, 0.1)" strokeOpacity={0} />
              ))}
              <XAxis dataKey="date" ticks={monthTicks} tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }}
                tickLine={false} axisLine={{ stroke: "hsla(220, 15%, 25%, 0.3)" }}
                tickFormatter={(v) => { const d = v.split("-"); return `${d[0].slice(2)}.${d[1]}`; }} />
              <YAxis tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={(v) => `${v.toFixed(1)}%`}>
                <Label value="10Y-2Y 금리차 (%)" angle={-90} position="insideLeft" offset={-5}
                  style={{ fill: "hsl(210, 90%, 60%)", fontSize: 11, fontWeight: 600 }} />
              </YAxis>
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="hsla(220, 15%, 50%, 0.6)" strokeDasharray="6 3">
                <Label value="역전 기준 (0%)" position="insideTopRight" fill="hsl(220, 10%, 55%)" fontSize={10} />
              </ReferenceLine>
              {(data.normalization_points || []).map((point, i) => (
                <ReferenceLine key={`norm-${i}`} x={point.date} stroke="hsl(40, 95%, 55%)" strokeDasharray="4 4">
                  <Label value={point.label} position="top" fill="hsl(40, 95%, 55%)" fontSize={10} fontWeight="bold" />
                </ReferenceLine>
              ))}
              <defs>
                <linearGradient id="spreadGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(210, 90%, 60%)" stopOpacity={0.3} />
                  <stop offset="50%" stopColor="hsl(210, 90%, 60%)" stopOpacity={0.05} />
                  <stop offset="50%" stopColor="hsl(0, 80%, 60%)" stopOpacity={0.05} />
                  <stop offset="100%" stopColor="hsl(0, 80%, 60%)" stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="spread" name="10Y-2Y 금리차" stroke="hsl(210, 90%, 60%)"
                fill="url(#spreadGradient)" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: "hsl(210, 90%, 60%)" }} />
            </AreaChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(210, 90%, 60%)" }} />10Y-2Y 금리차 (양수 = 정상)</div>
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(0, 80%, 60%)" }} />역전 구간 (음수 = 침체 시그널)</div>
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(40, 95%, 55%)" }} />정상화 시점 (침체 진입 주의)</div>
          </div>
          <div className="chart-guide">
            <p><strong>📘 지표 해설</strong></p>
            <p>• <b>장단기 금리차 (10Y-2Y)</b>: 미국 10년 국채 금리 - 2년 국채 금리. 경기 사이클의 가장 정확한 선행 지표.</p>
            <p>• <b>양수 (+1% 이상)</b>: 경기 확장 기대. 정상적인 수익률 곡선, 투자에 우호적.</p>
            <p>• <b>0~0.5%</b>: 경기 둔화 우려 시작. 수익률곡선 평탄화 → 연준 긴축 영향.</p>
            <p>• <b>음수 (역전)</b>: 역사적으로 6~18개월 내 경기 침체 확률 85%+. 2000년, 2006년, 2019년 모두 역전 후 침체 진입.</p>
            <p>• <b>역전→정상화</b>: 가장 위험한 시점! 역전이 풀리는 시점이 실제 침체 시작 시그널 (노란색 마커).</p>
            <p style={{color: "var(--text-tertiary)", marginTop: "4px"}}>데이터 출처: FRED T10Y2Y 시리즈 (미국 연방준비은행 공식 데이터)</p>
          </div>
        </>
      )}
    </ChartCard>
  );
}
