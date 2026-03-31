"use client";

import { useEffect } from "react";
import Header from "../components/layout/Header";
import ExchangeDivergence from "../components/macro/ExchangeDivergence";
import VolatilityIndex from "../components/macro/VolatilityIndex";
import LiquidityIndicator from "../components/macro/LiquidityIndicator";
import LeadingIndicator from "../components/macro/LeadingIndicator";
import SectorStrength from "../components/macro/SectorStrength";
import MacroSummary from "../components/macro/MacroSummary";

import ScreeningTable from "../components/screening/ScreeningTable";
import ScreeningSummary from "../components/screening/ScreeningSummary";

import PortfolioAnalysis from "../components/portfolio/PortfolioAnalysis";
import PortfolioSummary from "../components/portfolio/PortfolioSummary";

import OverallSummary from "../components/common/OverallSummary";
import { useAIAnalysis } from "../hooks/useAIAnalysis";

export default function DashboardPage() {
  const { 
    aiComments, 
    signals, 
    compAnalysis, 
    isCompLoading, 
    triggerComprehensiveAnalysis 
  } = useAIAnalysis();

  // 초기 로딩 시 통합 분석 1회 실행 (포트폴리오 없음)
  useEffect(() => {
    triggerComprehensiveAnalysis();
  }, []);

  // 포트폴리오 분석 완료 시 통합 분석 재실행
  const handlePortfolioAnalysis = (portfolioResult) => {
    triggerComprehensiveAnalysis(portfolioResult);
  };

  return (
    <>
      <Header />

      <main className="dashboard-container">
        {/* ============================================
            섹션 1: 거시/시장 환경 (Macro Dashboard)
            ============================================ */}
        <section className="dashboard-section" style={{ marginTop: "32px" }}>
          <div className="section-header">
            <span className="section-number">SECTION 01</span>
            <h2 className="section-title">거시 · 시장 환경</h2>
            <span className="section-subtitle">
              Macro Dashboard — 최근 1년 기준 주요 거시지표
            </span>
          </div>

          <ExchangeDivergence
            aiComment={aiComments?.exchange_comment}
            signals={signals?.exchange?.signals}
          />

          <VolatilityIndex
            aiComment={aiComments?.volatility_comment}
            signals={signals?.volatility?.signals}
          />

          <LiquidityIndicator
            aiComment={aiComments?.liquidity_comment}
            signals={signals?.liquidity?.signals}
          />

          <LeadingIndicator
            aiComment={aiComments?.leading_comment}
            signals={signals?.leading?.signals}
          />

          <SectorStrength
            aiComment={aiComments?.sector_comment}
            signals={signals?.sector?.signals}
          />

          {/* 거시 경제 AI 요약 */}
          <MacroSummary data={compAnalysis?.macro} />
        </section>

        {/* ============================================
            섹션 2: 시장 유망주 스크리닝
            ============================================ */}
        <section className="dashboard-section">
          <div className="section-header">
            <span className="section-number">SECTION 02</span>
            <h2 className="section-title">시장 유망주 스크리닝</h2>
            <span className="section-subtitle">
              Micro Analysis — KOSPI/KOSDAQ 시가총액 상위 종목 스코어링
            </span>
          </div>

          <ScreeningTable />

          {/* 시장 유망주 AI 요약 */}
          <ScreeningSummary data={compAnalysis?.screening} />
        </section>

        {/* ============================================
            섹션 3: 포트폴리오 분석
            ============================================ */}
        <section className="dashboard-section">
          <div className="section-header">
            <span className="section-number">SECTION 03</span>
            <h2 className="section-title">포트폴리오 리스크 관리</h2>
            <span className="section-subtitle">
              Portfolio — 내 보유 주식 기술적 지표 및 수익률 분석
            </span>
          </div>

          <PortfolioAnalysis onAnalysisComplete={handlePortfolioAnalysis} />

          {/* 포트폴리오 AI 요약 */}
          <PortfolioSummary data={compAnalysis?.portfolio} />
        </section>

        {/* ============================================
            마무리: 전체 통합 요약
            ============================================ */}
        <section className="dashboard-section" style={{ marginBottom: "64px" }}>
          <div className="section-header">
            <span className="section-number">CONCLUSION</span>
            <h2 className="section-title">종합 투자 전략</h2>
            <span className="section-subtitle">
              Overall Strategy — 모든 지표와 포트폴리오를 고려한 최종 제언
            </span>
          </div>

          {isCompLoading ? (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--text-tertiary)" }}>
              🤖 AI가 종합 전략을 수립 중입니다...
            </div>
          ) : (
            <OverallSummary data={compAnalysis?.overall} />
          )}
        </section>

        {/* 푸터 */}
        <footer
          style={{
            textAlign: "center",
            padding: "32px 0 48px",
            color: "var(--text-tertiary)",
            fontSize: "0.75rem",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <p>
            📊 Stock Investment Dashboard v1.0 — 데이터 출처: yfinance,
            DART, FRED, ECOS, 네이버금융 | AI: Gemini 2.0 Flash
          </p>
          <p style={{ marginTop: "4px" }}>
            본 대시보드는 투자 참고용이며, 투자 판단의 책임은 본인에게 있습니다.
          </p>
        </footer>
      </main>
    </>
  );
}

