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

// 부모(StockPage)가 API로 이미 받아온 historyData를 받음
const StockChart = ({ ticker, historyData }) => {
  
  // 데이터가 없거나 넘어오는 중일 때 예외 처리 구역
  if (!historyData || historyData.length === 0) {
    return <div className="chart-loading">최근 1년 주가 데이터가 존재하지 않습니다.</div>;
  }

  const formattedData = historyData.map((item) => ({
    ...item,
    displayDate: item.list_date.substring(5), // 월-일만 잘라내기
  }));

  return (
    <div className="chart-card-container">
      <div className="chart-header">
        <h2 className="chart-title">{ticker} 최근 1년 주가 추이</h2>
        <span className="chart-subtitle">총 {formattedData.length} 거래일 데이터</span>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={formattedData} margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
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