"use client";

import dynamic from "next/dynamic";
import { MatrixResponse } from "@/lib/types";
import { heatmapDisplay } from "@/lib/labels";

const Plot = dynamic(() =>
  Promise.all([
    import("react-plotly.js/factory"),
    // @ts-expect-error - no types available for this specific dist
    import("plotly.js-cartesian-dist")
  ]).then(([factoryModule, plotlyModule]) => {
    const createPlotComponent = factoryModule.default;
    const Plotly = plotlyModule.default || plotlyModule;
    return createPlotComponent(Plotly);
  }),
  { ssr: false }
);

function HeatmapCard({ title, data }: { title: string; data: MatrixResponse }) {
  const n = data.tickers.length;
  const leftMargin = n > 15 ? 120 : 80;
  const bottomMargin = n > 15 ? 120 : 80;
  const minH = n > 15 ? 550 : 400;
  return (
    <div className="rounded border border-border p-2 bg-surface">
      <div className="w-full h-full min-h-[350px]" style={{ minHeight: `${minH}px` }}>
        <Plot
          key={data.tickers.join("-") + title}
          data={[
            {
              z: data.matrix,
              x: data.tickers.map(heatmapDisplay),
              y: data.tickers.map(heatmapDisplay),
              type: "heatmap",
              colorscale: "RdBu",
              zmin: -1,
              zmax: 1,
              hoverongaps: false,
              texttemplate: "%{z:.2f}",
              showscale: false,
            },
          ]}
          layout={{
            title: { text: title, font: { color: "#e5e5e5", size: 14 } },
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            margin: { t: 40, l: leftMargin, r: 20, b: bottomMargin },
            xaxis: { tickfont: { color: "#e5e5e5", size: n > 15 ? 9 : 11 }, tickangle: -45 },
            yaxis: { tickfont: { color: "#e5e5e5", size: n > 15 ? 9 : 11 }, autorange: "reversed" },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "100%", minHeight: `${minH}px` }}
        />
      </div>
    </div>
  );
}

export default function CorrelationHeatmap({
  recent,
  longTerm,
  staticRecent,
  staticAll,
}: {
  recent: MatrixResponse | null;
  longTerm: MatrixResponse | null;
  staticRecent: MatrixResponse | null;
  staticAll: MatrixResponse | null;
}) {
  if (!recent || !longTerm || !staticRecent || !staticAll) {
    return <div className="card h-[400px] animate-pulse" />;
  }

  return (
    <div className="card">
      <h3 className="text-xl font-semibold mb-2 text-accent">Correlation Matrices</h3>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <HeatmapCard title="Kalman Fast (短期动态)" data={recent} />
        <HeatmapCard title="Kalman Smooth (长期动态)" data={longTerm} />
        <HeatmapCard title="近5日静态相关" data={staticRecent} />
        <HeatmapCard title="全历史静态相关" data={staticAll} />
      </div>
    </div>
  );
}
