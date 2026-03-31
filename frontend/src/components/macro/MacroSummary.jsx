"use client";

import AIPanel from "../common/AIPanel";

export default function MacroSummary({ data }) {
  if (!data) return null;

  return (
    <AIPanel title="거시 경제 AI 요약" icon="🌍">
      {data.summary}
      <div style={{ marginTop: "12px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <div style={{ padding: "8px", borderRadius: "8px", background: "rgba(255,255,255,0.03)", fontSize: "0.8rem" }}>
          <strong style={{ display: "block", marginBottom: "4px", color: "var(--text-tertiary)" }}>주요 코멘트</strong>
          <ul style={{ margin: 0, paddingLeft: "15px", color: "var(--text-secondary)" }}>
            <li>{data.exchange_comment}</li>
            <li>{data.volatility_comment}</li>
          </ul>
        </div>
        <div style={{ padding: "8px", borderRadius: "8px", background: "rgba(255,255,255,0.03)", fontSize: "0.8rem" }}>
          <strong style={{ display: "block", marginBottom: "4px", color: "var(--text-tertiary)" }}>시장 흐름</strong>
          <ul style={{ margin: 0, paddingLeft: "15px", color: "var(--text-secondary)" }}>
            <li>{data.liquidity_comment}</li>
            <li>{data.leading_comment}</li>
          </ul>
        </div>
      </div>
    </AIPanel>
  );
}
