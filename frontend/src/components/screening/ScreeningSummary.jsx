"use client";

import AIPanel from "../common/AIPanel";

export default function ScreeningSummary({ data }) {
  if (!data) return null;

  return (
    <AIPanel title="시장 유망주 AI 요약" icon="🔍">
      {data.summary}
      <div style={{ marginTop: "12px", padding: "10px", borderRadius: "8px", background: "rgba(210, 85, 55, 0.05)", border: "1px solid rgba(210, 85, 55, 0.1)" }}>
        <strong style={{ display: "block", marginBottom: "4px", color: "hsl(210, 85, 55%)", fontSize: "0.85rem" }}>
          💡 AI 추천 Top Pick 사유
        </strong>
        <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          {data.top_pick_reason}
        </p>
      </div>
    </AIPanel>
  );
}
