"use client";

/**
 * 시장 유망주 스크리닝 테이블 v2
 * -- PER/PBR/ROE/PEG + 매출/영업이익 성장률 + 재무효율성
 * -- 섹터 컬럼 제거, 현재가(날짜) 표시
 * -- DART 기반 정확 산출 + yfinance 교차검증 결과
 */

import { useState } from "react";
import useSWR from "swr";
import ChartCard from "../common/ChartCard";
import { fetcher } from "../../hooks/useApi";

const SIGNAL_STYLES = {
  "강력매수": { bg: "hsla(150, 70%, 45%, 0.15)", color: "hsl(150, 70%, 45%)", icon: "🟢" },
  "매수": { bg: "hsla(210, 80%, 55%, 0.15)", color: "hsl(210, 85%, 55%)", icon: "🔵" },
  "관망": { bg: "hsla(40, 90%, 55%, 0.12)", color: "hsl(40, 95%, 55%)", icon: "🟡" },
  "주의": { bg: "hsla(30, 90%, 55%, 0.12)", color: "hsl(30, 90%, 55%)", icon: "🟠" },
  "매도": { bg: "hsla(0, 80%, 55%, 0.15)", color: "hsl(0, 85%, 60%)", icon: "🔴" },
};

const SORT_OPTIONS = [
  { key: "score", label: "종합 스코어", desc: true },
  { key: "per", label: "PER (낮은순)", desc: false },
  { key: "pbr", label: "PBR (낮은순)", desc: false },
  { key: "roe", label: "ROE (높은순)", desc: true },
  { key: "peg", label: "PEG (낮은순)", desc: false },
  { key: "revenue_growth", label: "매출 성장률", desc: true },
];

/** 값의 상태에 따른 색상 */
function getColor(val, goodThreshold, badThreshold, invertGood = false) {
  if (val == null) return "var(--text-tertiary)";
  if (invertGood) {
    // 낮을수록 좋음 (PER, PEG)
    if (val <= goodThreshold) return "hsl(150, 70%, 50%)";
    if (val >= badThreshold) return "hsl(0, 80%, 60%)";
    return "var(--text-secondary)";
  }
  // 높을수록 좋음 (ROE, 성장률)
  if (val >= goodThreshold) return "hsl(150, 70%, 50%)";
  if (val <= badThreshold) return "hsl(0, 80%, 60%)";
  return "var(--text-secondary)";
}

export default function ScreeningTable({ aiComment, signals: externalSignals }) {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/screening/top-picks?limit=10",
    fetcher,
    { refreshInterval: 3600000, revalidateOnFocus: false, errorRetryCount: 2 }
  );
  const [sortKey, setSortKey] = useState("score");
  const [sortDesc, setSortDesc] = useState(true);

  const picks = data?.top_picks || [];
  const methodology = data?.methodology;

  // 정렬
  const sorted = [...picks].sort((a, b) => {
    const va = a[sortKey] ?? (sortDesc ? -Infinity : Infinity);
    const vb = b[sortKey] ?? (sortDesc ? -Infinity : Infinity);
    return sortDesc ? vb - va : va - vb;
  });

  const handleSort = (key, desc) => {
    if (sortKey === key) {
      setSortDesc(!sortDesc);
    } else {
      setSortKey(key);
      setSortDesc(desc);
    }
  };

  return (
    <ChartCard
      title="유망 종목 Top 10"
      icon="🏆"
      description="DART 공시 기반 정밀 분석: PER/PBR/ROE/PEG + 매출·영업이익 성장률 + 재무효율성"
      isLoading={isLoading}
      error={error}
      onRetry={() => mutate()}
      aiComment={aiComment}
      signals={externalSignals}
    >
      {sorted.length > 0 && (
        <>
          {data?.is_sample && (
            <div style={{
              background: "hsla(40, 90%, 55%, 0.08)", border: "1px solid hsla(40, 90%, 55%, 0.2)",
              borderRadius: "6px", padding: "8px 12px", marginBottom: "12px",
              fontSize: "0.75rem", color: "hsl(40, 95%, 55%)",
            }}>
              ⚠️ 샘플 데이터입니다. DART API Key 설정 후 실제 데이터로 전환됩니다.
            </div>
          )}

          {/* 컨트롤러 (정렬 + 엑셀) */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", gap: "10px", flexWrap: "wrap" }}>
            <div className="toggle-group">
              {SORT_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  className={`toggle-btn ${sortKey === opt.key ? "active" : ""}`}
                  onClick={() => handleSort(opt.key, opt.desc)}
                  style={{ fontSize: "0.7rem" }}
                >
                  {opt.label} {sortKey === opt.key ? (sortDesc ? "▼" : "▲") : ""}
                </button>
              ))}
            </div>
            
            <button 
              className="action-btn"
              onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/screening/export`, "_blank")}
              style={{
                fontSize: "0.7rem", 
                padding: "6px 12px", 
                borderRadius: "6px",
                background: "hsla(150, 70%, 45%, 0.15)",
                color: "hsl(150, 70%, 45%)",
                border: "1px solid hsla(150, 70%, 45%, 0.3)",
                cursor: "pointer",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "4px"
              }}
            >
              📥 Excel 다운로드 (수식 포함)
            </button>
          </div>

          {/* 테이블 */}
          <div style={{ overflowX: "auto" }}>
            <table className="screening-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>종목</th>
                  <th>현재가 (날짜)</th>
                  <th style={{ color: "hsl(150, 70%, 60%)" }}>2025 매출(억)</th>
                  <th style={{ color: "hsl(150, 70%, 60%)" }}>영업이익/률</th>
                  <th>PER</th>
                  <th>PBR</th>
                  <th>ROE</th>
                  <th>PEG</th>
                  <th>매출성장</th>
                  <th>효율</th>
                  <th>스코어</th>
                  <th>시그널</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((stock, i) => {
                  const sig = SIGNAL_STYLES[stock.signal] || SIGNAL_STYLES["관망"];
                  return (
                    <tr key={stock.stock_code}>
                      <td style={{ color: "var(--text-tertiary)" }}>{i + 1}</td>
                      <td>
                        <span style={{ fontWeight: 600 }}>{stock.name}</span>
                        <br />
                        <span style={{ fontSize: "0.65rem", color: "var(--text-tertiary)" }}>{stock.stock_code}</span>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>
                        {stock.price?.toLocaleString()}
                        {stock.price_date && (
                          <span style={{ fontSize: "0.6rem", color: "var(--text-tertiary)", display: "block" }}>
                            ({stock.price_date})
                          </span>
                        )}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", textAlign: "right" }}>
                        {stock.revenue?.toLocaleString() || "-"}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <span style={{ fontFamily: "var(--font-mono)", display: "block" }}>
                          {stock.operating_income?.toLocaleString() || "-"}
                        </span>
                        <span style={{ fontSize: "0.65rem", color: getColor(stock.operating_margin, 15, 5, false) }}>
                          ({stock.operating_margin ? `${stock.operating_margin}%` : "-"})
                        </span>
                      </td>
                      <td style={{
                        fontFamily: "var(--font-mono)",
                        color: getColor(stock.per, 10, 25, true),
                      }}>
                        {stock.per ?? "-"}
                      </td>
                      <td style={{
                        fontFamily: "var(--font-mono)",
                        color: getColor(stock.pbr, 1, 3, true),
                      }}>
                        {stock.pbr ?? "-"}
                      </td>
                      <td style={{
                        fontFamily: "var(--font-mono)",
                        color: getColor(stock.roe, 15, 5, false),
                      }}>
                        {stock.roe != null ? `${stock.roe}%` : "-"}
                      </td>
                      <td style={{
                        fontFamily: "var(--font-mono)",
                        color: getColor(stock.peg, 1, 2, true),
                      }}>
                        {stock.peg != null ? stock.peg : "-"}
                        {stock.peg != null && stock.peg <= 1 && (
                          <span title="PEG ≤ 1: 저평가 성장주" style={{ marginLeft: 4 }}>✨</span>
                        )}
                      </td>
                      <td style={{
                        fontFamily: "var(--font-mono)",
                        color: getColor(stock.revenue_growth, 10, 0, false),
                      }}>
                        {stock.revenue_growth != null ? `${stock.revenue_growth > 0 ? "+" : ""}${stock.revenue_growth}%` : "-"}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        {stock.financial_efficiency === true && (
                          <span title="재고자산증가율 < 매출성장률" style={{ color: "hsl(150, 70%, 50%)" }}>✅</span>
                        )}
                        {stock.financial_efficiency === false && (
                          <span title="재고자산증가율 ≥ 매출성장률" style={{ color: "hsl(0, 80%, 60%)" }}>⚠️</span>
                        )}
                        {stock.financial_efficiency == null && "-"}
                      </td>
                      <td>
                        <div className="score-bar">
                          <div
                            className="score-fill"
                            style={{ width: `${stock.score || 0}%` }}
                          />
                          <span className="score-text">{stock.score}</span>
                        </div>
                      </td>
                      <td>
                        <span className="screening-signal" style={{
                          background: sig.bg,
                          color: sig.color,
                          border: `1px solid ${sig.color}33`,
                        }}>
                          {sig.icon} {stock.signal}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="chart-guide" style={{ marginTop: "16px" }}>
            <p><strong>📘 스크리닝 방법론 v2.1</strong></p>
            <p>• <b>2025 매출/영업이익</b>: 전년도(y-1) 확정 또는 추정 실적. 단위: 억원 (DART 기반).</p>
            <p>• <b>PEG (주가/성장 비율)</b>: PER ÷ EPS 성장률. ≤1이면 성장 대비 저평가(✨). 피터 린치 지표.</p>
            <p>• <b>재무효율</b>: 재고자산 증가율 &lt; 매출 성장률이면 ✅ (건전한 재고 관리).</p>
            <p>• <b>교차검증</b>: 야후 파이낸스와 네이버 금융 데이터를 대조하여 지수의 무결성 확보.</p>
            <p style={{ color: "var(--text-tertiary)", marginTop: "4px" }}>
              데이터 출처: DART(재무), 야후/네이버(시세) | 엑셀 다운로드 시 모든 산출 근거 데이터와 직접 검증 가능한 수식이 포함됩니다.
            </p>
          </div>
        </>
      )}
    </ChartCard>
  );
}
