import "./globals.css";

export const metadata = {
  title: "📊 주식 투자 판단 대시보드",
  description:
    "거시 경제, 시장 스크리닝, 포트폴리오 분석 기반 투자 의사결정 대시보드",
  keywords: "주식, 투자, 대시보드, 거시경제, KOSPI, S&P500, VIX",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
