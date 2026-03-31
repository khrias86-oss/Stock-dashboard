"use client";

/**
 * 그래프 5: 주요 섹터 ETF 상대강도
 * -- 4개 섹터의 KOSPI 대비 상대 수익률, 0선 기준
 * -- 자동차 벤치마킹: 개별 종목 On/Off 토글
 */

import { useState } from "react";
import useSWR from "swr";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Label,
} from "recharts";
import ChartCard from "../common/ChartCard";
import { fetcher, swrOptions } from "../../hooks/useApi";

const SECTOR_COLORS = {
  "반도체": "hsl(210, 90%, 60%)", "2차전지": "hsl(150, 70%, 50%)",
  "자동차": "hsl(35, 95%, 60%)", "금융": "hsl(280, 70%, 65%)",
  "바이오": "hsl(330, 70%, 60%)", "방산": "hsl(15, 85%, 55%)",
  "에너지/화학": "hsl(170, 60%, 50%)", "IT/소프트웨어": "hsl(260, 65%, 60%)",
};
const BENCHMARK_COLORS = {
  "현대차": "hsl(20, 90%, 55%)", "기아": "hsl(45, 90%, 55%)",
  "토요타": "hsl(0, 80%, 60%)", "테슬라": "hsl(200, 90%, 60%)",
};

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
          {entry.name}: {entry.value != null ? `${entry.value > 0 ? "+" : ""}${Number(entry.value).toFixed(2)}%` : "N/A"}
        </p>
      ))}
    </div>
  );
}

function isMonthStart(dateStr) {
  if (!dateStr) return false;
  return parseInt(dateStr.split("-")[2], 10) <= 3;
}

export default function SectorStrength({ aiComment, signals: externalSignals }) {
  const { data, error, isLoading, mutate } = useSWR("/api/macro/sector-strength", fetcher, swrOptions);
  const [activeSectors, setActiveSectors] = useState(new Set(["반도체", "2차전지", "자동차", "금융", "바이오", "방산", "에너지/화학", "IT/소프트웨어"]));
  const [activeBenchmarks, setActiveBenchmarks] = useState(new Set());
  const [showBenchmark, setShowBenchmark] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const hasData = data?.sectors && Object.keys(data.sectors).length > 0;

  const toggleSector = (name) => {
    setActiveSectors((prev) => { const next = new Set(prev); if (next.has(name)) next.delete(name); else next.add(name); return next; });
  };
  const toggleBenchmark = (name) => {
    setActiveBenchmarks((prev) => { const next = new Set(prev); if (next.has(name)) next.delete(name); else next.add(name); return next; });
  };

  const mergeData = () => {
    if (!hasData) return [];
    const dateMap = {};
    for (const [name, series] of Object.entries(data.sectors)) {
      if (!activeSectors.has(name)) continue;
      for (const item of series) { if (!dateMap[item.date]) dateMap[item.date] = { date: item.date }; dateMap[item.date][name] = item.value; }
    }
    if (showBenchmark && data.auto_benchmarks) {
      for (const [name, series] of Object.entries(data.auto_benchmarks)) {
        if (!activeBenchmarks.has(name)) continue;
        for (const item of series) { if (!dateMap[item.date]) dateMap[item.date] = { date: item.date }; dateMap[item.date][name] = item.value; }
      }
    }
    return Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
  };

  const chartData = mergeData();
  const monthTicks = chartData.filter((d) => isMonthStart(d.date)).map((d) => d.date);

  return (
    <ChartCard title="섹터 ETF 상대강도" icon="🔥"
      description="KOSPI 대비 섹터 수익률 (0선 위 = KOSPI 아웃퍼폼)"
      isLoading={isLoading} error={error} onRetry={() => mutate()}
      aiComment={aiComment} signals={externalSignals}>
      {hasData && (
        <>
          <div className="toggle-group" style={{ marginBottom: "12px" }}>
            {Object.keys(SECTOR_COLORS).map((name) => (
              <button key={name} className={`toggle-btn ${activeSectors.has(name) ? "active" : ""}`}
                onClick={() => toggleSector(name)}
                style={activeSectors.has(name) ? { borderColor: SECTOR_COLORS[name], color: SECTOR_COLORS[name], background: `${SECTOR_COLORS[name]}15` } : {}}>
                {name}
              </button>
            ))}
            <button className={`toggle-btn ${showBenchmark ? "active" : ""}`} onClick={() => setShowBenchmark(!showBenchmark)}
              style={{ marginLeft: "8px" }}>🚗 자동차 벤치마킹</button>
          </div>
          {showBenchmark && data.auto_benchmarks && (
            <div className="toggle-group" style={{ marginBottom: "12px" }}>
              {Object.keys(BENCHMARK_COLORS).map((name) => (
                <button key={name} className={`toggle-btn ${activeBenchmarks.has(name) ? "active" : ""}`}
                  onClick={() => toggleBenchmark(name)}
                  style={activeBenchmarks.has(name) ? { borderColor: BENCHMARK_COLORS[name], color: BENCHMARK_COLORS[name], background: `${BENCHMARK_COLORS[name]}15` } : {}}>
                  {name}
                </button>
              ))}
            </div>
          )}
          <div style={{ marginBottom: "12px" }}>
            <button className={`toggle-btn ${showSources ? "active" : ""}`}
              onClick={() => setShowSources(!showSources)}
              style={{ fontSize: "0.7rem" }}>📋 산출 근거 보기</button>
          </div>
          {showSources && data.sector_sources && (
            <div style={{
              background: "hsla(220, 15%, 15%, 0.5)", borderRadius: "8px", padding: "12px",
              marginBottom: "16px", fontSize: "0.72rem", lineHeight: "1.8",
              border: "1px solid var(--border-subtle)",
            }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ color: "var(--text-tertiary)", textAlign: "left" }}>
                    <th style={{ padding: "4px 8px" }}>섹터</th>
                    <th style={{ padding: "4px 8px" }}>대표 ETF</th>
                    <th style={{ padding: "4px 8px" }}>선정 근거</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.sector_sources).map(([name, info]) => (
                    <tr key={name} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "4px 8px", color: SECTOR_COLORS[name] || "var(--text-primary)", fontWeight: 600 }}>{name}</td>
                      <td style={{ padding: "4px 8px", color: "var(--text-secondary)" }}>{info.etf}</td>
                      <td style={{ padding: "4px 8px", color: "var(--text-tertiary)" }}>{info.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p style={{ marginTop: "8px", color: "var(--text-tertiary)", fontStyle: "italic" }}>
                ※ 한국 ETF는 yfinance에서 불안정 → 동일 섹터 글로벌 대표 ETF로 대체하여 상대강도 비교
              </p>
            </div>
          )}
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, bottom: 5, left: 20 }}>
              <XAxis dataKey="date" ticks={monthTicks} tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }}
                tickLine={false} axisLine={{ stroke: "hsla(220, 15%, 25%, 0.3)" }}
                tickFormatter={(v) => { const d = v.split("-"); return `${d[0].slice(2)}.${d[1]}`; }} />
              <YAxis tick={{ fill: "hsl(220, 10%, 45%)", fontSize: 10 }} tickLine={false} axisLine={false}
                tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`}>
                <Label value="상대강도 (섹터 - KOSPI) %" angle={-90} position="insideLeft" offset={-5}
                  style={{ fill: "hsl(220, 15%, 70%)", fontSize: 11, fontWeight: 600 }} />
              </YAxis>
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="hsla(220, 15%, 50%, 0.4)" strokeDasharray="4 4" />
              {Object.entries(SECTOR_COLORS).map(([name, color]) =>
                activeSectors.has(name) ? <Line key={name} type="monotone" dataKey={name} name={name} stroke={color} strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls /> : null
              )}
              {showBenchmark && Object.entries(BENCHMARK_COLORS).map(([name, color]) =>
                activeBenchmarks.has(name) ? <Line key={name} type="monotone" dataKey={name} name={name} stroke={color} strokeWidth={1.5} strokeDasharray="4 2" dot={false} activeDot={{ r: 3 }} connectNulls /> : null
              )}
            </LineChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            {Object.entries(SECTOR_COLORS).map(([name, color]) => activeSectors.has(name) ? <div key={name} className="legend-item"><span className="legend-dot" style={{ background: color }} />{name}</div> : null)}
            {showBenchmark && Object.entries(BENCHMARK_COLORS).map(([name, color]) => activeBenchmarks.has(name) ? <div key={name} className="legend-item"><span className="legend-dot" style={{ background: color, borderRadius: "2px" }} />{name}</div> : null)}
          </div>
          <div className="chart-guide">
            <p><strong>📘 지표 해설</strong></p>
            <p>• <b>상대강도</b>: (섹터 ETF 수익률 - KOSPI 수익률). 0선 위 = 해당 섹터가 KOSPI보다 강함(아웃퍼폼).</p>
            <p>• <b>양수 (+10% 이상)</b>: 해당 섹터에 강한 모멘텀. 해당 섹터 종목 매수 검토.</p>
            <p>• <b>0% 부근</b>: KOSPI와 비슷한 성과. 시장 평균 수준.</p>
            <p>• <b>음수</b>: KOSPI 대비 부진한 섹터. 해당 섹터 종목 비중 축소 검토.</p>
            <p>• <b>섹터 순환</b>: 상대강도가 하락→상승으로 전환되는 섹터 = &quot;로테이션 진입&quot; 신호.</p>
            <p style={{color: "var(--text-tertiary)", marginTop: "4px"}}>※ 한국 ETF 대신 동일 산업 글로벌 ETF로 대체 (📋 산출 근거 버튼으로 상세 확인)</p>
          </div>
        </>
      )}
    </ChartCard>
  );
}
