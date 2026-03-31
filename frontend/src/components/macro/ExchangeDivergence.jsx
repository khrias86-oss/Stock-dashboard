"use client";

/**
 * 그래프 1: 환율 및 외국인 수급 다이버전스
 * -- 원/달러 환율 + 달러인덱스 (좌측 Y축) / 거래량 (우측 Y축) 오버레이
 * -- 다이버전스 구간: 환율↑ + 매수↑ 비정상 구간을 형광 하이라이트
 */

import useSWR from "swr";
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  Label,
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
        </p>
      ))}
    </div>
  );
}

function isMonthStart(dateStr) {
  if (!dateStr) return false;
  return parseInt(dateStr.split("-")[2], 10) <= 3;
}

export default function ExchangeDivergence({ aiComment, signals: externalSignals }) {
  const { data, error, isLoading, mutate } = useSWR("/api/macro/exchange-divergence", fetcher, swrOptions);
  const hasData = data?.series?.length > 0;

  const getSignalBadge = () => {
    if (!hasData) return null;
    const zones = data.divergence_zones || [];
    const lastDate = data.series[data.series.length - 1]?.date;
    const inDivergence = zones.some((z) => z.end >= lastDate);
    if (inDivergence) return <span className="signal-badge warning">⚡ 다이버전스 감지</span>;
    return <span className="signal-badge safe">정상</span>;
  };

  const monthTicks = hasData ? data.series.filter((d) => isMonthStart(d.date)).map((d) => d.date) : [];

  return (
    <ChartCard title="환율 & 외국인 수급 다이버전스" icon="💱"
      description="원/달러 환율↑ + 외국인 매수↑ 비정상 구간을 자동 감지합니다"
      badge={getSignalBadge()} isLoading={isLoading} error={error} onRetry={() => mutate()}
      aiComment={aiComment} signals={externalSignals}>
      {hasData && (
        <>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={data.series} margin={{ top: 5, right: 70, bottom: 5, left: 20 }}>
              {(data.divergence_zones || []).map((zone, i) => (
                <ReferenceArea key={i} x1={zone.start} x2={zone.end} fill="hsla(55, 100%, 50%, 0.1)" strokeOpacity={0} />
              ))}
              <XAxis dataKey="date" ticks={monthTicks} tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }}
                tickLine={false} axisLine={{ stroke: "hsla(220, 15%, 25%, 0.3)" }}
                tickFormatter={(v) => { const d = v.split("-"); return `${d[0].slice(2)}.${d[1]}`; }} />
              <YAxis yAxisId="left" tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }} tickLine={false} axisLine={false} domain={[1000, 1600]}>
                <Label value="원/달러 환율 (원)" angle={-90} position="insideLeft" offset={-5}
                  style={{ fill: "hsl(210, 90%, 60%)", fontSize: 11, fontWeight: 600 }} />
              </YAxis>
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }} tickLine={false} axisLine={false} domain={["auto", "auto"]}>
                <Label value="달러 인덱스 (DXY)" angle={90} position="insideRight" offset={-5}
                  style={{ fill: "hsl(280, 70%, 65%)", fontSize: 11, fontWeight: 600 }} />
              </YAxis>
              <Tooltip content={<CustomTooltip />} />
              <Line yAxisId="left" type="monotone" dataKey="usd_krw" name="원/달러" stroke="hsl(210, 90%, 60%)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="dxy" name="달러인덱스" stroke="hsl(280, 70%, 65%)" strokeWidth={1.5} dot={false} strokeDasharray="4 2" activeDot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(210, 90%, 60%)" }} />원/달러 환율 (좌측)</div>
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsl(280, 70%, 65%)" }} />달러 인덱스 DXY (우측)</div>
            <div className="legend-item"><span className="legend-dot" style={{ background: "hsla(55, 100%, 50%, 0.5)" }} />다이버전스 구간</div>
          </div>
          <div className="chart-guide">
            <p><strong>📘 지표 해설</strong></p>
            <p>• <b>원/달러 환율</b>: 원화의 달러 대비 가치. ↑ 원화 약세(위험 신호), ↓ 원화 강세(안정).</p>
            <p>• <b>달러 인덱스 (DXY)</b>: 6개 주요 통화 대비 달러 강도. 100 미만=달러 약세, 100 이상=달러 강세.</p>
            <p>• <b>다이버전스</b>: 환율↑ + DXY↓ 동시 발생 구간. 원화 약세가 달러 강세가 아닌 다른 요인(자본 유출 등)에 기인함을 의미합니다.</p>
            <p style={{color: "var(--text-tertiary)", marginTop: "4px"}}>판단 기준: 환율 1,300원 이상 = 경계, 1,400원 이상 = 위험, 1,200원 이하 = 안정</p>
          </div>
        </>
      )}
    </ChartCard>
  );
}
