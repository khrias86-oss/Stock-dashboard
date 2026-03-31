"use client";

/**
 * 공통 차트 카드 래퍼
 * -- 로딩/에러/빈 데이터 상태를 일관되게 처리
 * -- AI 코멘트 표시 기능 포함
 * -- 모든 거시지표 차트에서 재사용
 */

export default function ChartCard({
  title,
  icon,
  description,
  badge,
  children,
  isLoading,
  error,
  onRetry,
  aiComment,   // AI 분석 의견 (1~2줄)
  signals,     // 시그널 엔진 결과 [{type, msg}]
}) {
  return (
    <div className="chart-card fade-in">
      <div className="chart-card-header">
        <div>
          <div className="chart-title">
            {icon && <span>{icon}</span>}
            {title}
          </div>
          {description && <p className="chart-description">{description}</p>}

          {/* AI 분석 의견 (제목 바로 아래) */}
          {aiComment && (
            <div className="ai-comment">
              <span className="ai-comment-icon">🤖</span>
              <span className="ai-comment-text">{aiComment}</span>
            </div>
          )}

          {/* 시그널 배지들 */}
          {signals && signals.length > 0 && (
            <div className="signal-list">
              {signals.slice(0, 3).map((sig, i) => (
                <span key={i} className={`signal-badge ${sig.type}`}>
                  {sig.type === "danger" ? "🔴" : sig.type === "warning" ? "🟡" : "🟢"} {sig.msg}
                </span>
              ))}
            </div>
          )}
        </div>
        {badge && badge}
      </div>

      <div className="chart-body">
        {isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <span className="loading-text">데이터를 불러오는 중...</span>
          </div>
        ) : error ? (
          <div className="error-container">
            <span className="error-icon">⚠️</span>
            <p className="error-message">
              {error.message || "데이터를 불러올 수 없습니다."}
            </p>
            {onRetry && (
              <button className="retry-btn" onClick={onRetry}>
                다시 시도
              </button>
            )}
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
