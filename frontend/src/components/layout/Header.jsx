"use client";

/**
 * 대시보드 헤더 컴포넌트
 * -- 로고, 시장 상태(개장/폐장), 현재 시간 표시
 */

import { useState, useEffect } from "react";

export default function Header() {
  const [currentTime, setCurrentTime] = useState("");
  const [marketOpen, setMarketOpen] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hours = now.getHours();
      const minutes = now.getMinutes();

      // 한국 장 시간: 9:00 ~ 15:30 (평일만)
      const day = now.getDay();
      const isWeekday = day >= 1 && day <= 5;
      const timeInMinutes = hours * 60 + minutes;
      const isMarketHours = timeInMinutes >= 540 && timeInMinutes <= 930; // 9:00~15:30
      setMarketOpen(isWeekday && isMarketHours);

      setCurrentTime(
        now.toLocaleString("ko-KR", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        })
      );
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="dashboard-header">
      <div className="header-content">
        <div className="header-title">
          <span className="logo-icon">📊</span>
          <h1>Stock Investment Dashboard</h1>
        </div>
        <div className="header-meta">
          <div className="market-status">
            <span className={`dot ${marketOpen ? "open" : "closed"}`} />
            <span>{marketOpen ? "KRX 장중" : "KRX 장 마감"}</span>
          </div>
          <span className="header-time">{currentTime}</span>
        </div>
      </div>
    </header>
  );
}
