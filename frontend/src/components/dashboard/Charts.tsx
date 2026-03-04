import React from "react";

// --- Simple Line Chart ---

interface LineChartProps {
    data: { date: string; value: number }[];
    color?: string;
    height?: number;
    loading?: boolean;
}

export function SimpleLineChart({ data, color = "#10B981", height = 200, loading }: LineChartProps) {
    if (loading) {
        return <div className={`w-full bg-slate-50 animate-pulse rounded-lg`} style={{ height }} />;
    }

    if (!data || data.length === 0) {
        return (
            <div className="w-full flex items-center justify-center text-slate-400 text-sm" style={{ height }}>
                No data available
            </div>
        );
    }

    // Calculate scaling
    const containerHeight = height;
    const padding = 20;
    const chartHeight = containerHeight - padding * 2;

    // Y-Axis
    const maxValue = Math.max(...data.map(d => d.value));
    // If max is 0, default to 10 to avoid division by zero
    const yMax = maxValue === 0 ? 10 : maxValue;

    // X-Axis
    const points = data.map((d, i) => {
        const x = (i / (data.length - 1)) * 100; // Percentage
        const y = padding + chartHeight - ((d.value / yMax) * chartHeight);
        return `${x},${y}`;
    });

    // Generate Path
    // Since we use vector-effect="non-scaling-stroke", we can use 0-100 coordinate space for X
    // But for Y we need pixel values usually or viewbox magic. 
    // Let's use a fixed viewBox 1000xHeight to keep it simple and precise? 
    // Actually, just standard percentages in specific way or strict pixels.
    // simpler: valid SVG path logic.

    // Let's normalize X to 0-1000 and Y to 0-Height
    const width = 1000;
    const normalizedPoints = data.map((d, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = padding + chartHeight - ((d.value / yMax) * chartHeight);
        return `${x},${y}`;
    }).join(" ");

    return (
        <div className="w-full overflow-hidden" style={{ height }}>
            <svg viewBox={`0 0 ${width} ${containerHeight}`} className="w-full h-full overflow-visible">
                {/* Grid lines (optional) */}
                <line x1="0" y1={padding + chartHeight} x2={width} y2={padding + chartHeight} stroke="currentColor" className="text-slate-200 dark:text-slate-800" strokeWidth="1" />
                <line x1="0" y1={padding} x2={width} y2={padding} stroke="currentColor" className="text-slate-100 dark:text-slate-800/50" strokeDasharray="4 4" strokeWidth="1" />

                {/* Polyline */}
                <polyline
                    fill="none"
                    stroke={color}
                    strokeWidth="3"
                    points={normalizedPoints}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />

                {/* Dots */}
                {data.map((d, i) => {
                    const x = (i / (data.length - 1)) * width;
                    const y = padding + chartHeight - ((d.value / yMax) * chartHeight);
                    return (
                        <circle key={i} cx={x} cy={y} r="4" fill="var(--card)" stroke={color} strokeWidth="2" />
                    );
                })}
            </svg>
            <div className="flex justify-between mt-2 text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-widest px-1">
                <span>{data[0]?.date && new Date(data[0].date).toLocaleDateString()}</span>
                <span>{data[data.length - 1]?.date && new Date(data[data.length - 1].date).toLocaleDateString()}</span>
            </div>
        </div>
    );
}

// --- Simple Bar Chart ---

interface BarChartProps {
    data: { label: string; value: number; color: string }[];
    height?: number;
    loading?: boolean;
}

export function SimpleBarChart({ data, height = 200, loading }: BarChartProps) {
    if (loading) {
        return <div className={`w-full bg-slate-50 dark:bg-slate-800/50 animate-pulse rounded-lg`} style={{ height }} />;
    }

    if (!data || data.length === 0) {
        return (
            <div className="w-full flex items-center justify-center text-slate-400 text-sm" style={{ height }}>
                No data available
            </div>
        );
    }

    const maxValue = Math.max(...data.map(d => d.value));
    const yMax = maxValue === 0 ? 10 : maxValue;

    return (
        <div className="w-full flex items-end justify-around gap-2" style={{ height }}>
            {data.map((d) => {
                const heightPct = (d.value / yMax) * 100;
                // Min height 4px for visibility
                const safeHeight = Math.max(heightPct, 2);

                return (
                    <div key={d.label} className="flex flex-col items-center flex-1 group relative">
                        {/* Tooltipish value */}
                        <div className="absolute -top-6 text-xs font-bold text-slate-600 dark:text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity">
                            {d.value}
                        </div>

                        <div
                            className="w-full max-w-[40px] rounded-t-sm transition-all duration-500 ease-out hover:opacity-80"
                            style={{
                                height: `${safeHeight}%`,
                                backgroundColor: d.color
                            }}
                        />
                        <span className="text-[10px] uppercase font-medium text-slate-400 dark:text-slate-500 mt-2 tracking-wider text-center">
                            {d.label}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
