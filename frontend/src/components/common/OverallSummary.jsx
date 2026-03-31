"use client";

import AIPanel from "../common/AIPanel";

export default function OverallSummary({ data }) {
  if (!data) return null;

  return (
    <AIPanel 
      title="오늘의 투자 전략 (통합 요약)" 
      icon="🚀" 
      signal={data.signal}
      type="overall"
    >
      <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--text-primary)", marginBottom: "15px" }}>
        {data.summary}
      </div>
      
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "10px", marginTop: "16px" }}>
        <div style={{ 
          padding: "12px", 
          borderRadius: "12px", 
          background: "rgba(255, 255, 255, 0.05)", 
          border: "1px solid rgba(255, 255, 255, 0.1)" 
        }}>
          <strong style={{ display: "block", marginBottom: "8px", color: "var(--text-tertiary)", fontSize: "0.8rem", letterSpacing: "1px" }}>
            ACTION ITEMS
          </strong>
          <ul style={{ margin: 0, paddingLeft: "20px", color: "var(--text-secondary)" }}>
            {data.key_actions.map((action, i) => (
              <li key={i} style={{ marginBottom: "4px" }}>{action}</li>
            ))}
          </ul>
        </div>
      </div>
      
      <div style={{ 
        marginTop: "16px", 
        textAlign: "right", 
        fontSize: "0.7rem", 
        color: "var(--text-tertiary)",
        fontStyle: "italic" 
      }}>
        * 본 분석은 마켓 시그널과 AI 엔진에 의해 생성되었습니다. 실제 투자 전 전문가와 상의하세요.
      </div>
    </AIPanel>
  );
}
