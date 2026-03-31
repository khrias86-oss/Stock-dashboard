/**
 * API 데이터 페칭을 위한 커스텀 훅
 * -- SWR 기반으로 자동 캐싱, 리페치, 에러 핸들링 제공
 */

// 후행 슬래시(/)를 제거하여 중복 슬래시 문제 방지
const rawUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE = rawUrl.replace(/\/$/, "");

if (typeof window !== "undefined") {
  console.log("🌐 Current API BASE:", API_BASE);
  if (rawUrl === "http://localhost:8000") {
    console.warn("⚠️ Warning: NEXT_PUBLIC_API_URL is missing. Falling back to localhost.");
  }
}

/**
 * SWR용 기본 fetcher 함수
 * - 응답이 ok가 아니면 에러를 throw (SWR이 에러 상태로 전환)
 */
export const fetcher = async (url) => {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) {
    const error = new Error("데이터를 불러오는 데 실패했습니다.");
    error.status = res.status;
    throw error;
  }
  return res.json();
};

/**
 * SWR 공통 옵션
 * - 5분마다 자동 갱신
 * - 포커스 시 재검증
 * - 에러 시 3초 후 재시도
 */
export const swrOptions = {
  revalidateOnFocus: true,
  refreshInterval: 5 * 60 * 1000, // 5분
  errorRetryInterval: 3000,
  errorRetryCount: 3,
  dedupingInterval: 60000, // 1분 내 중복 요청 방지
};
