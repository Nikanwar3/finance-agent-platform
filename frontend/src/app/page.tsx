"use client";
import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { PlayCircle, CheckCircle, Clock } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

type Company = {
  id: string;
  name: string;
  industry: string;
  revenue_annual: number;
  employees: number;
  status: string;
  progress: number;
};

type ActionLog = {
  id: number;
  agent_name: string;
  company_id: string;
  action: string;
  details: string;
  timestamp: string;
};

const API_BASE = "http://localhost:8000/api";

export default function Dashboard() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [logs, setLogs] = useState<ActionLog[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchData = async () => {
    try {
      const [{ data: comps }, { data: logsData }] = await Promise.all([
        axios.get(`${API_BASE}/companies`),
        axios.get(`${API_BASE}/logs`)
      ]);
      setCompanies(comps);
      setLogs(logsData);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();

    // Auto-refresh interval (polling fallback while actual WebSocket updates happen)
    const interval = setInterval(fetchData, 3000);

    const connectWs = () => {
      const socket = new WebSocket("ws://localhost:8000/api/ws");
      socket.onmessage = (event) => {
        fetchData(); // Simplistic refresh on update
      };

      socket.onclose = () => {
        setTimeout(connectWs, 5000); // Retry logic
      };
      wsRef.current = socket;
    }

    connectWs();

    return () => {
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleStartClose = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await axios.post(`${API_BASE}/close/${id}`);
      fetchData(); // Optimistic refresh
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartAll = async () => {
    try {
      // Small delay between starts to simulate batch orchestration
      for (const c of companies) {
        if (c.status !== 'completed' && c.status !== 'in_progress') {
          await axios.post(`${API_BASE}/close/${c.id}`);
        }
      }
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6 lg:p-8 font-sans selection:bg-blue-500/30">
      <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center">
        <div>
          <h1 className="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400 mb-2 drop-shadow-[0_0_15px_rgba(96,165,250,0.3)]">
            Apex Capital Partners
          </h1>
          <h2 className="text-gray-400 text-sm font-medium tracking-wide uppercase">Month-End Close Orchestration</h2>
        </div>
        <button
          onClick={handleStartAll}
          className="mt-4 md:mt-0 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-lg transition-all shadow-[0_0_20px_rgba(79,70,229,0.4)] hover:shadow-[0_0_25px_rgba(79,70,229,0.6)] font-semibold tracking-wide flex items-center gap-2 group border border-indigo-400/30">
          <PlayCircle className="w-5 h-5 group-hover:scale-110 transition-transform" />
          Run All Portfolios
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
        <div className="lg:col-span-2 space-y-6 lg:space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 lg:gap-6">
            {companies.map((c) => (
              <div key={c.id} className="bg-gray-800/80 backdrop-blur-sm rounded-xl p-5 border border-gray-700/50 hover:border-indigo-500/50 transition-all hover:shadow-[0_0_30px_rgba(79,70,229,0.1)] cursor-default group relative overflow-hidden flex flex-col justify-between" style={{ minHeight: '130px' }}>

                <div className="absolute top-0 left-0 w-full h-1 bg-gray-700/30">
                  <div
                    className="h-full transition-all duration-1000 ease-out"
                    style={{
                      width: `${c.progress}%`,
                      backgroundColor: c.progress === 100 ? '#10b981' : c.status === "in_progress" ? '#F59E0B' : '#4f46e5',
                      boxShadow: c.progress === 100 ? '0 0 10px #10b981' : c.status === "in_progress" ? '0 0 10px #F59E0B' : 'none'
                    }}
                  />
                </div>

                <div>
                  <div className="flex justify-between items-start mb-3 mt-2">
                    <h3 className="font-bold text-lg leading-tight line-clamp-2 pr-2 text-gray-100" title={c.name}>{c.name}</h3>
                    {c.status === "completed" ? (
                      <CheckCircle className="text-emerald-400 w-6 h-6 shrink-0 filter drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]" />
                    ) : c.status === "in_progress" ? (
                      <Clock className="text-amber-400 w-6 h-6 animate-pulse shrink-0 drop-shadow-[0_0_5px_rgba(245,158,11,0.5)]" />
                    ) : (
                      <PlayCircle className="text-indigo-400 w-6 h-6 cursor-pointer hover:text-indigo-300 shrink-0 transition-all hover:scale-110" onClick={(e) => handleStartClose(c.id, e)} />
                    )}
                  </div>
                  <div className="text-xs font-semibold text-gray-400 mb-5 uppercase tracking-wider">{c.industry}</div>
                </div>

                <div className="flex justify-between items-end mt-4 pt-4 border-t border-gray-700/50">
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold mb-1 uppercase tracking-wider">ARR</div>
                    <div className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-br from-white to-gray-400">${(c.revenue_annual / 1000000).toFixed(1)}M</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] text-gray-500 font-bold mb-1 uppercase tracking-wider">Close</div>
                    <div className="text-lg font-black tracking-tight" style={{ color: c.progress === 100 ? '#10b981' : c.status === "in_progress" ? '#F59E0B' : '#6b7280' }}>{c.progress}%</div>
                  </div>
                </div>

              </div>
            ))}
          </div>

          <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl p-6 border border-gray-700/50 shadow-[0_10px_40px_-15px_rgba(0,0,0,0.5)] w-full">
            <h3 className="text-xl font-bold mb-6 text-gray-100 flex items-center gap-2">
              <div className="w-1.5 h-6 bg-indigo-500 rounded-full shadow-[0_0_10px_rgba(79,70,229,0.8)]"></div>
              Portfolio Revenue Overview
            </h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={companies} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} tickMargin={10} />
                  <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value / 1000000}M`} />
                  <Tooltip
                    cursor={{ fill: 'rgba(79,70,229,0.1)' }}
                    contentStyle={{ backgroundColor: 'rgba(17,24,39,0.9)', border: '1px solid rgba(75,85,99,0.8)', borderRadius: '12px', backdropFilter: 'blur(8px)', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)' }}
                    labelStyle={{ color: '#e5e7eb', marginBottom: '8px', fontWeight: 'bold' }}
                    itemStyle={{ color: '#818cf8', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="revenue_annual" name="Revenue" fill="url(#colorUv)" radius={[6, 6, 0, 0]} maxBarSize={50} />
                  <defs>
                    <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#818cf8" stopOpacity={1} />
                      <stop offset="100%" stopColor="#4f46e5" stopOpacity={0.8} />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl border border-gray-700/50 h-[calc(100vh-8rem)] min-h-[500px] flex flex-col relative overflow-hidden shadow-[0_10px_40px_-15px_rgba(0,0,0,0.5)]">
          <div className="absolute -top-32 -right-32 w-64 h-64 bg-indigo-500 opacity-10 blur-[100px] pointer-events-none rounded-full"></div>

          <div className="p-5 border-b border-gray-700/50 flex justify-between items-center bg-gray-800/95 z-10 sticky top-0 shadow-sm">
            <h3 className="text-lg font-bold text-gray-100 flex items-center gap-2">
              <div className="w-1.5 h-5 bg-indigo-500 rounded-full shadow-[0_0_10px_rgba(79,70,229,0.8)]"></div>
              Agent Activity Feed
            </h3>
            <div className="flex items-center gap-2 bg-gray-900 px-3 py-1.5 border border-gray-700/50 rounded-full">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping absolute opacity-75"></div>
              <div className="w-2 h-2 rounded-full bg-emerald-500 relative shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
              <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-bold">Live Sync</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto space-y-4 pr-3 pl-5 py-5 custom-scrollbar relative z-0">
            {logs.length === 0 ? (
              <div className="text-gray-500 text-sm text-center mt-10 flex flex-col items-center justify-center h-full opacity-60">
                <Clock className="w-12 h-12 mb-4 text-gray-600" />
                <p>System is monitoring.</p>
                <p className="text-xs mt-1">Ready for autonomous actions.</p>
              </div>
            ) : logs.map((log, index) => (
              <div key={log.id} className="relative group pl-6 pb-2">
                {/* Timeline connector */}
                {index !== logs.length - 1 && (
                  <div className="absolute left-[11px] top-6 bottom-[-20px] w-[2px] bg-gray-700/50 group-hover:bg-indigo-500/30 transition-colors"></div>
                )}

                {/* Timeline dot */}
                <div className="absolute left-0 top-1.5 w-[24px] h-[24px] rounded-full bg-gray-900 border-2 border-indigo-500 flex items-center justify-center shadow-[0_0_10px_rgba(79,70,229,0.3)] z-10">
                  <div className="w-2 h-2 rounded-full bg-indigo-400"></div>
                </div>

                <div className="bg-gray-900/50 border border-gray-700/40 hover:border-indigo-500/30 hover:bg-gray-800/80 transition-all duration-300 rounded-lg p-3.5 shadow-sm">
                  <div className="flex justify-between items-start mb-2 gap-2">
                    <span className="text-[11px] text-indigo-400 font-black uppercase tracking-widest">{log.agent_name}</span>
                    <span className="text-[10px] text-gray-500 font-medium bg-gray-950 px-2 py-0.5 border border-gray-800 rounded-md shrink-0">
                      {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-gray-200 leading-snug">{log.action}</div>
                  <div className="text-[13px] text-gray-400 mt-2 leading-relaxed font-medium">{log.details}</div>

                  {log.company_id && (
                    <div className="mt-3 pt-3 border-t border-gray-800 flex justify-between items-center">
                      <div className="text-[10px] bg-indigo-500/10 text-indigo-300 px-2 py-1 flex items-center gap-1.5 rounded font-bold tracking-wider">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400"></div>
                        {log.company_id.replace(/_/g, ' ').toUpperCase()}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
