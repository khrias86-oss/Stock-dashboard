"use client";

/**
 * AI 분석 데이터 훅
 * -- /api/ai/macro-analysis 엔드포인트에서 시그널 + AI 의견을 가져옴
 * -- 10분 리프레시 (AI 호출 빈도 최적화)
 */

import useSWR from "swr";
import { fetcher, API_BASE } from "./useApi";
import { useState } from "react";

// const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const AI_SWR_OPTIONS = {
  refreshInterval: 600000, // 10분
  revalidateOnFocus: false,
  dedupingInterval: 300000, // 5분 중복 방지
  errorRetryCount: 2,
};

export function useAIAnalysis() {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/ai/macro-analysis",
    fetcher,
    AI_SWR_OPTIONS
  );

  const [compAnalysis, setCompAnalysis] = useState(null);
  const [isCompLoading, setIsCompLoading] = useState(false);

  // 통합 분석 트리거 (포트폴리오 데이터 포함 가능)
  const triggerComprehensiveAnalysis = async (portfolioResult = null) => {
    setIsCompLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/ai/comprehensive-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portfolio: portfolioResult }),
      });
      const resData = await resp.json();
      if (resData.status === "success") {
        setCompAnalysis(resData.ai_analysis);
        // 거시지표 시그널이 업데이트되었을 수 있으므로 SWR 데이터도 갱신 (선택사항)
        if (resData.macro_signals) {
          mutate({ ...data, signals: resData.macro_signals }, false);
        }
      }
    } catch (e) {
      console.error("통합 AI 분석 실패:", e);
    } finally {
      setIsCompLoading(false);
    }
  };

  return {
    // 기존 Macro Analysis 결과 (호환성)
    aiComments: data?.ai_comments || null,
    signals: data?.signals || null,
    
    // 신규 Comprehensive Analysis 결과
    compAnalysis,
    isCompLoading,
    triggerComprehensiveAnalysis,
    
    isLoading,
    error,
    isAI: data?.ai_comments?.is_ai !== false,
  };
}

