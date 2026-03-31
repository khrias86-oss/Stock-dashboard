"use client";

import AIPanel from "../common/AIPanel";

export default function PortfolioSummary({ data }) {
  if (!data) return null;

  return (
    <AIPanel title="포트폴리오 리스크 진단" icon="💼">
      {data.summary}
      <div style={{ 
        marginTop: "12px", 
        padding: "10px", 
        borderRadius: "8px", 
        background: "hsla(0, 85%, 60%, 0.05)", 
        border: "1px solid hsla(0, 85%, 60%, 0.1)",
        display: "flex",
        alignItems: "center",
        gap: "10px"
      }}>
        <span style={{ fontSize: "1.2rem" }}>⚖️</span>
        <div>
          <strong style={{ display: "block", color: "hsl(0, 85%, 60%)", fontSize: "0.85rem" }}>리밸런싱 팁</strong>
          <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            {data.rebalance_tip}
          </p>
        </div>
      </div>
    </AIPanel>
  );
}
