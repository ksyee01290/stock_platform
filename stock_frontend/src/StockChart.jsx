import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import "./App.css"; 

const StockChart = ({ ticker }) => {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);

  // 마지막으로 서버에 요청한 종목 코드 기억
  const lastFetchedTicker = useRef("");

  useEffect(() => {
    if (!ticker) return;
    if (lastFetchedTicker.current === ticker) return;

    setLoading(true);
    // 요청 보내는 순간 창고에 현재 종목을 박제
    lastFetchedTicker.current =ticker;
    axios
      .get(`http://127.0.0.1:8000/api/stocks/${ticker}/history`)
      .then((response) => {
        const formattedData = response.data.map((item) => ({
          ...item,
          displayDate: item.list_date.substring(5),
        }));
        setChartData(formattedData);
        setLoading(false);
      })
      .catch((error) => {
        console.error("데이터를 가져오는 중 에러 발생:", error);
        setLoading(false);
        lastFetchedTicker.current = "";
      });
  }, [ticker]);

  if (!ticker){
    return <div className="chart-loading">상단에서 종목을 검색하시면 최근 1년 주가 추이 그래프가 출력됩니다.</div>;
  }

  if (loading) {
    return <div className="chart-loading">10년 치 시계열 창고에서 최근 1년 치 주가를 정밀 조회 중...</div>;
  }

  return (
    <div className="chart-card-container">
      <div className="chart-header">
        <h2 className="chart-title">{ticker} 최근 1년 주가 추이</h2>
        <span className="chart-subtitle">총 {chartData.length} 거래일 데이터</span>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData} margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="displayDate" stroke="#888888" fontSize={12} tickLine={false} />
            <YAxis domain={["dataMin - 5", "dataMax + 5"]} stroke="#888888" fontSize={12} tickLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1e293b", borderRadius: "8px", color: "#fff", border: "none" }}
              labelStyle={{ fontWeight: "bold", color: "#38bdf8" }}
            />
            <Legend verticalAlign="top" height={36} />
            <Line
              name="종가 (Close)"
              type="monotone"
              dataKey="close_price"
              stroke="#0ea5e9"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default StockChart;