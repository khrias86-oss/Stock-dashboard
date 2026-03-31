"use client";

/**
 * AI 분석 요약 패널 (공통 컴포넌트)
 * -- 프리미엄 디자인: 글라스모피즘, 그라데이션 보더, 애니메이션
 */

export default function AIPanel({ title, icon, children, signal, type = "default" }) {
  const getSignalColor = () => {
    switch (signal) {
      case "강력매수": return "hsl(150, 70%, 50%)";
      case "매수": return "hsl(210, 85%, 55%)";
      case "관망": return "hsl(40, 95%, 55%)";
      case "주의": return "hsl(30, 90%, 55%)";
      case "매도": return "hsl(0, 85%, 60%)";
      default: return "var(--text-secondary)";
    }
  };

  const signalColor = getSignalColor();

  return (
    <div className={`ai-panel ai-panel-${type}`} style={{
      position: "relative",
      padding: "20px",
      borderRadius: "16px",
      background: "linear-gradient(135deg, hsla(220, 20%, 15%, 0.8), hsla(220, 20%, 10%, 0.9))",
      border: "1px solid hsla(220, 15%, 25%, 0.5)",
      backdropFilter: "blur(12px)",
      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
      marginTop: "24px",
      overflow: "hidden"
    }}>
      {/* 장식용 배경 광원 */}
      <div style={{
        position: "absolute",
        top: "-50px",
        right: "-50px",
        width: "150px",
        height: "150px",
        background: `radial-gradient(circle, ${signalColor}22 0%, transparent 70%)`,
        zIndex: 0
      }} />

      <div style={{ position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
          <span style={{ fontSize: "1.5rem" }}>{icon}</span>
          <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary)" }}>{title}</h3>
          {signal && (
            <span style={{
              marginLeft: "auto",
              padding: "4px 12px",
              borderRadius: "20px",
              fontSize: "0.75rem",
              fontWeight: 700,
              background: `${signalColor}22`,
              color: signalColor,
              border: `1px solid ${signalColor}44`
            }}>
              {signal}
            </span>
          )}
        </div>
        <div style={{ 
          fontSize: "0.95rem", 
          lineHeight: "1.6", 
          color: "var(--text-secondary)",
          whiteSpace: "pre-line" 
        }}>
          {children}
        </div>
      </div>
    </div>
  );
}
