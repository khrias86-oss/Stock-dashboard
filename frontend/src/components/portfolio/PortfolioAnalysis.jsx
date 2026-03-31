"use client";

/**
 * 포트폴리오 업로드 + 분석 결과 테이블
 * -- CSV 드래그앤드롭 / 수동 입력 지원
 * -- 종목별 RSI/볼린저/MACD 시그널
 * -- 포트폴리오 요약 (총 수익률, 섹터 비중)
 */

import { useState, useCallback } from "react";
import ChartCard from "../common/ChartCard";
import { API_BASE } from "../../hooks/useApi";

// const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SIGNAL_COLORS = {
  "매수": "hsl(150, 70%, 45%)",
  "보유": "hsl(210, 85%, 55%)",
  "관망": "hsl(40, 95%, 55%)",
  "주의": "hsl(30, 90%, 55%)",
  "매도": "hsl(0, 85%, 60%)",
};

export default function PortfolioAnalysis({ aiComment, signals: externalSignals, onAnalysisComplete }) {
  const [holdings, setHoldings] = useState(null);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isSample, setIsSample] = useState(false);
  const [inputMode, setInputMode] = useState("manual"); // "manual" | "csv"
  const [manualInputs, setManualInputs] = useState([
    { account: "주계좌", code: "", buy_price: "", quantity: "" },
  ]);
  const [csvText, setCsvText] = useState("");

  // API 호출
  const fetchAnalysis = async (body) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/api/portfolio/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (data.status === "success") {
        setHoldings(data.holdings);
        setSummary(data.summary);
        setIsSample(data.is_sample || false);
        if (onAnalysisComplete) {
          onAnalysisComplete({ holdings: data.holdings, summary: data.summary });
        }
      } else {
        setError(data.error || "분석에 실패했습니다.");
      }
    } catch (e) {
      setError("서버 연결에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  // 샘플 포트폴리오 로드
  const loadSample = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/api/portfolio/sample`);
      const data = await resp.json();
      if (data.status === "success") {
        setHoldings(data.holdings);
        setSummary(data.summary);
        setIsSample(true);
        if (onAnalysisComplete) {
          onAnalysisComplete({ holdings: data.holdings, summary: data.summary });
        }
      }
    } catch (e) {
      setError("샘플 로드 실패");
    } finally {
      setIsLoading(false);
    }
  };

  // 수동 입력 제출
  const submitManual = () => {
    const items = manualInputs
      .filter((r) => r.code && r.buy_price && r.quantity)
      .map((r) => ({
        account: r.account,
        code: r.code,
        buy_price: parseFloat(r.buy_price),
        quantity: parseInt(r.quantity),
      }));
    if (!items.length) return setError("종목을 입력해주세요.");
    fetchAnalysis({ items });
  };

  // CSV 제출
  const submitCsv = () => {
    if (!csvText.trim()) return setError("CSV를 입력해주세요.");
    fetchAnalysis({ csv: csvText });
  };

  // 수동 입력 행 추가/변경
  const addRow = () =>
    setManualInputs([...manualInputs, { account: "주계좌", code: "", buy_price: "", quantity: "" }]);
  const updateRow = (i, field, value) => {
    const next = [...manualInputs];
    next[i][field] = value;
    setManualInputs(next);
  };
  const removeRow = (i) => setManualInputs(manualInputs.filter((_, j) => j !== i));

  // CSV 드래그앤드롭
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setCsvText(ev.target.result);
        setInputMode("csv");
      };
      reader.readAsText(file);
    }
  }, []);

  return (
    <ChartCard
      title="포트폴리오 분석"
      icon="💼"
      description="보유 종목 입력 → RSI/볼린저/MACD 기술적 분석 + 수익률 계산"
      isLoading={isLoading}
      error={error}
      onRetry={() => setError(null)}
      aiComment={aiComment}
      signals={externalSignals}
    >
      {/* 입력 UI (분석 결과가 없을 때만 표시) */}
      {!holdings && (
        <div className="portfolio-input-area">
          <div className="toggle-group" style={{ marginBottom: "16px" }}>
            <button className={`toggle-btn ${inputMode === "manual" ? "active" : ""}`}
              onClick={() => setInputMode("manual")}>✍️ 수동 입력</button>
            <button className={`toggle-btn ${inputMode === "csv" ? "active" : ""}`}
              onClick={() => setInputMode("csv")}>📄 CSV 입력</button>
            <button className="toggle-btn" onClick={loadSample}
              style={{ marginLeft: "auto" }}>🧪 샘플 데이터 분석</button>
            <a href={`${API_BASE}/api/portfolio/sample-csv`} download className="toggle-btn"
              style={{ textDecoration: "none", display: "inline-block", marginLeft: "8px", background: "var(--bg-card)", color: "var(--text-primary)" }}>
              📥 샘플 CSV 다운로드
            </a>
          </div>

          {inputMode === "manual" && (
            <div>
              <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "12px" }}>
                <thead>
                  <tr style={{ color: "var(--text-tertiary)", fontSize: "0.72rem" }}>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>계좌명</th>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>종목명(코드)</th>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>매수가(원)</th>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>수량</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {manualInputs.map((row, i) => (
                    <tr key={i}>
                      <td style={{ padding: "2px 4px" }}>
                        <input className="portfolio-input" placeholder="연금계좌"
                          value={row.account} onChange={(e) => updateRow(i, "account", e.target.value)} />
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        <input className="portfolio-input" placeholder="삼성전자 (또는 005930)"
                          value={row.code} onChange={(e) => updateRow(i, "code", e.target.value)} />
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        <input className="portfolio-input" placeholder="60000" type="number"
                          value={row.buy_price} onChange={(e) => updateRow(i, "buy_price", e.target.value)} />
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        <input className="portfolio-input" placeholder="100" type="number"
                          value={row.quantity} onChange={(e) => updateRow(i, "quantity", e.target.value)} />
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        {manualInputs.length > 1 && (
                          <button onClick={() => removeRow(i)}
                            style={{ background: "none", border: "none", color: "var(--text-tertiary)", cursor: "pointer" }}>✕</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ display: "flex", gap: "8px" }}>
                <button className="toggle-btn" onClick={addRow}>+ 종목 추가</button>
                <button className="toggle-btn active" onClick={submitManual}
                  style={{ marginLeft: "auto" }}>🔍 분석하기</button>
              </div>
            </div>
          )}

          {inputMode === "csv" && (
            <div>
              <div className="csv-drop-zone" onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}>
                <textarea className="csv-textarea" rows={6}
                  placeholder="계좌명,종목명,매수가,수량&#10;주계좌,삼성전자,60000,100&#10;주계좌,000660,155000,30&#10;연금계좌,NAVER,200000,10"
                  value={csvText} onChange={(e) => setCsvText(e.target.value)} />
                <p style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", marginTop: "4px" }}>
                  샘플 양식을 다운로드하여 복사 붙여넣기 할 수 있습니다. 종목코드 외에 종목명도 인식합니다.
                </p>
              </div>
              <button className="toggle-btn active" onClick={submitCsv}
                style={{ marginTop: "8px" }}>🔍 분석하기</button>
            </div>
          )}
        </div>
      )}

      {/* 분석 결과 */}
      {holdings && summary && (
        <>
          {/* 다시 입력 버튼 */}
          <button className="toggle-btn" onClick={() => { setHoldings(null); setSummary(null); }}
            style={{ marginBottom: "16px" }}>← 다시 입력</button>

          {isSample && (
            <div style={{
              background: "hsla(40, 90%, 55%, 0.08)", border: "1px solid hsla(40, 90%, 55%, 0.2)",
              borderRadius: "6px", padding: "8px 12px", marginBottom: "12px",
              fontSize: "0.75rem", color: "hsl(40, 95%, 55%)",
            }}>
              🧪 샘플 포트폴리오 분석 결과입니다.
            </div>
          )}

          {/* 포트폴리오 요약 카드 */}
          <div className="portfolio-summary-grid">
            <div className="portfolio-stat">
              <span className="stat-label">총 투자</span>
              <span className="stat-value">{summary.total_cost?.toLocaleString()}원</span>
            </div>
            <div className="portfolio-stat">
              <span className="stat-label">총 평가</span>
              <span className="stat-value">{summary.total_value?.toLocaleString()}원</span>
            </div>
            <div className="portfolio-stat">
              <span className="stat-label">평가손익</span>
              <span className="stat-value" style={{
                color: summary.total_pnl >= 0 ? "hsl(150, 70%, 50%)" : "hsl(0, 80%, 60%)",
              }}>
                {summary.total_pnl >= 0 ? "+" : ""}{summary.total_pnl?.toLocaleString()}원
              </span>
            </div>
            <div className="portfolio-stat">
              <span className="stat-label">수익률</span>
              <span className="stat-value" style={{
                color: summary.total_return >= 0 ? "hsl(150, 70%, 50%)" : "hsl(0, 80%, 60%)",
                fontSize: "1.1rem",
              }}>
                {summary.total_return >= 0 ? "+" : ""}{summary.total_return}%
              </span>
            </div>
          </div>

          {/* 계좌별 요약 */}
          {summary.accounts && Object.keys(summary.accounts).length > 1 && (
            <div style={{ marginTop: "12px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {Object.entries(summary.accounts).map(([acc, data]) => (
                <div key={acc} style={{
                  padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: "8px", border: "1px solid var(--border-color)", fontSize: "0.8rem"
                }}>
                  <strong style={{ color: "var(--text-primary)" }}>{acc}</strong>
                  <span style={{ 
                    marginLeft: "8px", fontWeight: "bold",
                    color: data.total_return >= 0 ? "hsl(150, 70%, 50%)" : "hsl(0, 80%, 60%)" 
                  }}>
                    {data.total_return >= 0 ? "+" : ""}{data.total_return}%
                  </span>
                  <div style={{ color: "var(--text-tertiary)", marginTop: "4px", fontSize: "0.75rem" }}>
                    평가: {data.total_value.toLocaleString()}원
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 종목별 분석 */}
          <div style={{ overflowX: "auto", marginTop: "16px" }}>
            <table className="screening-table">
              <thead>
                <tr>
                  <th>계좌</th>
                  <th>종목</th>
                  <th>매수가</th>
                  <th>현재가</th>
                  <th>수량</th>
                  <th>수익률</th>
                  <th>RSI</th>
                  <th>볼린저</th>
                  <th>MACD</th>
                  <th>판정</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => {
                  const sigColor = SIGNAL_COLORS[h.signal?.overall] || "var(--text-secondary)";
                  return (
                    <tr key={`${h.account}-${h.code}`}>
                      <td>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", background: "var(--bg-elevated)", padding: "2px 6px", borderRadius: "4px" }}>
                          {h.account || "기본계좌"}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600 }}>{h.name}</span>
                        <br />
                        <span style={{ fontSize: "0.65rem", color: "var(--text-tertiary)" }}>{h.code}</span>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>{h.buy_price?.toLocaleString()}</td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>{h.current_price?.toLocaleString()}</td>
                      <td style={{ fontFamily: "var(--font-mono)" }}>{h.quantity}</td>
                      <td style={{
                        fontFamily: "var(--font-mono)", fontWeight: 600,
                        color: h.return_pct >= 0 ? "hsl(150, 70%, 50%)" : "hsl(0, 80%, 60%)",
                      }}>
                        {h.return_pct >= 0 ? "+" : ""}{h.return_pct}%
                      </td>
                      <td style={{
                        fontFamily: "var(--font-mono)",
                        color: h.rsi >= 70 ? "hsl(0, 80%, 60%)" : h.rsi <= 30 ? "hsl(150, 70%, 50%)" : "var(--text-secondary)",
                      }}>
                        {h.rsi ?? "-"}
                      </td>
                      <td style={{ fontSize: "0.7rem" }}>
                        {h.bollinger?.position ?? "-"}
                        {h.bollinger?.pct_b != null && (
                          <span style={{ color: "var(--text-tertiary)", marginLeft: "4px" }}>
                            ({h.bollinger.pct_b}%)
                          </span>
                        )}
                      </td>
                      <td style={{
                        fontSize: "0.7rem",
                        color: h.macd?.cross === "골든크로스" ? "hsl(150, 70%, 50%)" :
                               h.macd?.cross === "데드크로스" ? "hsl(0, 80%, 60%)" : "var(--text-secondary)",
                      }}>
                        {h.macd?.cross !== "없음" ? h.macd?.cross : h.macd?.trend || "-"}
                      </td>
                      <td>
                        <span style={{
                          padding: "2px 8px", borderRadius: "10px", fontSize: "0.7rem", fontWeight: 600,
                          background: `${sigColor}18`, color: sigColor, border: `1px solid ${sigColor}33`,
                        }}>
                          {h.signal?.overall}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* 시그널 상세 */}
          {holdings.some((h) => h.signal?.signals?.length > 0) && (
            <div className="chart-guide" style={{ marginTop: "16px" }}>
              <p><strong>📋 종목별 시그널 상세</strong></p>
              {holdings.map((h) => (
                h.signal?.signals?.length > 0 && (
                  <div key={h.code} style={{ marginTop: "6px" }}>
                    <b>{h.name}</b>:
                    {h.signal.signals.map((s, i) => (
                      <span key={i} style={{
                        marginLeft: "8px", fontSize: "0.7rem",
                        color: s.type === "danger" ? "hsl(0, 80%, 60%)" :
                               s.type === "safe" ? "hsl(150, 70%, 50%)" : "var(--text-secondary)",
                      }}>
                        {s.msg}
                      </span>
                    ))}
                  </div>
                )
              ))}
            </div>
          )}

          {/* 해설 */}
          <div className="chart-guide" style={{ marginTop: "16px" }}>
            <p><strong>📘 지표 해설</strong></p>
            <p>• <b>RSI (14일)</b>: 70 이상 = 과매수(매도 검토), 30 이하 = 과매도(매수 검토), 50 중립.</p>
            <p>• <b>볼린저밴드 %B</b>: 100% 초과 = 상단 돌파(과열), 0% 미만 = 하단 이탈(반등 기대), 50% = 중간.</p>
            <p>• <b>MACD</b>: 골든크로스(매수), 데드크로스(매도). MACD선이 시그널선 위 = 상승 추세.</p>
            <p>• <b>종합 판정</b>: 위험 시그널 2개+ = 매도, 안전 시그널 2개+ = 매수, 그 외 보유/관망.</p>
          </div>
        </>
      )}
    </ChartCard>
  );
}
