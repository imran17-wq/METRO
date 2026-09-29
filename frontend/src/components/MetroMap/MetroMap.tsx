/**
 * MetroMap.tsx — Reusable SVG Metro Schematic Component.
 * Canonical 5-Line Network schematic map.
 */

import React, { useCallback, useMemo, useRef, useState } from "react";
import type { NetworkResponse, RouteResponse } from "../../types";
import { LINE_COLORS, LINE_STATUS } from "../../types";
import {
  PHYSICAL_STATIONS,
  INTERCHANGE_CAPSULES,
  METRO_LINE_PATHS,
  getStationGeometry,
} from "../../config/metroGeometry";
import type {
  StationGeometry,
  InterchangeCapsule,
} from "../../config/metroGeometry";

import type { Train } from "../../types";

interface MetroMapProps {
  network: NetworkResponse;
  route?: RouteResponse | null;
  trains?: Train[];
  selectedTrainId?: string | null;
  hoveredStation?: string | null;
  selectedStation?: string | null;
  onStationClick?: (stationId: string, stationName: string) => void;
  onTrainClick?: (trainId: string) => void;
  onStationHover?: (stationId: string | null) => void;
  className?: string;
}


interface TooltipState {
  x: number;
  y: number;
  name: string;
  line: string;
  nodeIds: string[];
  isInterchange: boolean;
}

const VIEW_WIDTH = 1600;
const VIEW_HEIGHT = 1100;

const STATION_RADIUS = 5;
const TERMINUS_RADIUS = 8;
const ROUTE_STATION_RADIUS = 7;
const ORIGIN_DEST_RADIUS = 10;

const CANONICAL_LINES = ["Purple", "Green", "Yellow", "Pink", "Blue"];

function getLineColor(line: string): string {
  return (LINE_COLORS as Record<string, string>)[line] ?? "#888888";
}

const MetroMap: React.FC<MetroMapProps> = ({
  network: _network,
  route,
  trains,
  selectedTrainId,
  hoveredStation,
  selectedStation,
  onStationClick,
  onTrainClick,
  onStationHover,
  className = "",
}) => {

  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const [scale, setScale] = useState<number>(1);
  const [pan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const routeNodeSet = useMemo(() => {
    return new Set(route?.station_ids ?? []);
  }, [route]);

  const originNodeId = route?.origin_id;
  const destNodeId = route?.destination_id;

  const routePoints = useMemo(() => {
    if (!route || !route.station_ids.length) return [];
    const pts: { x: number; y: number }[] = [];

    route.station_ids.forEach((nid) => {
      const geom = getStationGeometry(nid);
      if (geom) {
        pts.push({ x: geom.x, y: geom.y });
      }
    });
    return pts;
  }, [route]);

  const svgToViewBox = useCallback((e: React.MouseEvent) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    return { x: svgP.x, y: svgP.y };
  }, []);

  const handleStationHover = useCallback(
    (name: string, line: string, nodeIds: string[], isInterchange: boolean, e: React.MouseEvent) => {
      const pos = svgToViewBox(e);
      setTooltip({ x: pos.x, y: pos.y, name, line, nodeIds, isInterchange });
      onStationHover?.(nodeIds[0]);
    },
    [svgToViewBox, onStationHover]
  );

  const handleStationLeave = useCallback(() => {
    setTooltip(null);
    onStationHover?.(null);
  }, [onStationHover]);

  const handleZoomIn = () => setScale((prev) => Math.min(prev * 1.25, 2.5));
  const handleZoomOut = () => setScale((prev) => Math.max(prev / 1.25, 0.75));
  const handleResetZoom = () => setScale(1);

  return (
    <div className={`relative w-full h-full bg-[#0B0E14] overflow-hidden select-none ${className}`}>
      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 z-20 flex flex-col gap-1 bg-[#161B22]/90 backdrop-blur border border-[#30363D] rounded-lg p-1 shadow-lg">
        <button
          onClick={handleZoomIn}
          className="w-8 h-8 flex items-center justify-center text-cream/80 hover:text-cream hover:bg-[#21262D] rounded text-lg font-bold transition-colors"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          className="w-8 h-8 flex items-center justify-center text-cream/80 hover:text-cream hover:bg-[#21262D] rounded text-lg font-bold transition-colors"
          title="Zoom Out"
        >
          −
        </button>
        <button
          onClick={handleResetZoom}
          className="w-8 h-8 flex items-center justify-center text-cream/80 hover:text-cream hover:bg-[#21262D] rounded text-[10px] font-mono transition-colors"
          title="Fit to Network"
        >
          FIT
        </button>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        className="w-full h-full"
        role="img"
        aria-label="Bengaluru Metro canonical schematic map"
      >
        <defs>
          <pattern id="grid-pattern" width={40} height={40} patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#161B22" strokeWidth={0.5} />
          </pattern>
          <filter id="route-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <rect width={VIEW_WIDTH} height={VIEW_HEIGHT} fill="#0B0E14" />
        <rect width={VIEW_WIDTH} height={VIEW_HEIGHT} fill="url(#grid-pattern)" />

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${scale})`}>
          {/* ── 1. Line Base Paths ── */}
          {CANONICAL_LINES.map((line) => {
            const pathData = METRO_LINE_PATHS[line];
            if (!pathData) return null;
            const color = getLineColor(line);

            return (
              <g key={`line-${line}`}>
                <path
                  d={pathData}
                  fill="none"
                  stroke={color}
                  strokeWidth={9}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={0.35}
                />
                <path
                  d={pathData}
                  fill="none"
                  stroke={color}
                  strokeWidth={6}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={0.95}
                />
              </g>
            );
          })}


          {/* ── 2. Route Highlight ── */}
          {routePoints.length >= 2 && (
            <g className="route-highlight-group">
              <polyline
                points={routePoints.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                stroke="#F5F0E8"
                strokeWidth={10}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={0.5}
                filter="url(#route-glow)"
              />
              <polyline
                points={routePoints.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                stroke="#FFFFFF"
                strokeWidth={5}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={0.9}
              />
            </g>
          )}

          {/* ── 3. Interchange Pill Capsules (7 Hubs) ── */}
          {INTERCHANGE_CAPSULES.map((cap: InterchangeCapsule) => {
            const isHovered = cap.nodeIds.some((nid) => nid === hoveredStation);
            const isSelected = cap.nodeIds.some((nid) => nid === selectedStation);
            const isOnRoute = cap.nodeIds.some((nid) => routeNodeSet.has(nid));
            const isOrigin = cap.nodeIds.some((nid) => nid === originNodeId);
            const isDest = cap.nodeIds.some((nid) => nid === destNodeId);

            const capsuleFill = isOrigin
              ? "#22c55e"
              : isDest
              ? "#ef4444"
              : isOnRoute
              ? "#F5F0E8"
              : "#0B0E14";

            const capsuleStroke = isOrigin
              ? "#4ade80"
              : isDest
              ? "#f87171"
              : isHovered || isSelected || isOnRoute
              ? "#FFFFFF"
              : "#D0C9BE";

            return (
              <g
                key={cap.id}
                className="cursor-pointer"
                onClick={() => onStationClick?.(cap.nodeIds[0], cap.name)}
                onMouseEnter={(e) => handleStationHover(cap.name, cap.lines.join(" / "), cap.nodeIds, true, e)}
                onMouseLeave={handleStationLeave}
              >
                <rect
                  x={cap.x}
                  y={cap.y}
                  width={cap.width}
                  height={cap.height}
                  rx={cap.rx}
                  fill={capsuleFill}
                  stroke={capsuleStroke}
                  strokeWidth={isHovered || isSelected || isOnRoute ? 3 : 2}
                />
                <circle
                  cx={cap.x + 10}
                  cy={cap.y + cap.height / 2}
                  r={3}
                  fill={getLineColor(cap.lines[0] || "Purple")}
                />
                <circle
                  cx={cap.x + cap.width - 10}
                  cy={cap.y + cap.height / 2}
                  r={3}
                  fill={getLineColor(cap.lines[1] || cap.lines[0] || "Green")}
                />
                <text
                  x={cap.labelX}
                  y={cap.labelY}
                  textAnchor={cap.labelAnchor}
                  fontSize={12}
                  fontWeight="700"
                  fill={isHovered || isSelected ? "#FFFFFF" : "#F5F0E8"}
                  fontFamily="'Inter', system-ui, sans-serif"
                  style={{ pointerEvents: "none" }}
                >
                  {cap.name}
                </text>
              </g>
            );
          })}

          {/* ── 4. Standard Physical Stations ── */}
          {PHYSICAL_STATIONS.map((st: StationGeometry) => {
            if (st.isInterchange) return null;

            const isHovered = st.nodeIds.some((nid) => nid === hoveredStation);
            const isSelected = st.nodeIds.some((nid) => nid === selectedStation);
            const isOnRoute = st.nodeIds.some((nid) => routeNodeSet.has(nid));
            const isOrigin = st.nodeIds.some((nid) => nid === originNodeId);
            const isDest = st.nodeIds.some((nid) => nid === destNodeId);

            const lineColor = getLineColor(st.line);

            let radius = st.isTerminus ? TERMINUS_RADIUS : STATION_RADIUS;
            if (isOrigin || isDest) radius = ORIGIN_DEST_RADIUS;
            else if (isOnRoute) radius = ROUTE_STATION_RADIUS;

            const fillColor = isOrigin
              ? "#22c55e"
              : isDest
              ? "#ef4444"
              : isOnRoute
              ? "#FFFFFF"
              : isHovered || isSelected
              ? "#FFFFFF"
              : "#0B0E14";

            const strokeColor = isOrigin
              ? "#4ade80"
              : isDest
              ? "#f87171"
              : isOnRoute || isHovered || isSelected
              ? "#FFFFFF"
              : lineColor;

            const strokeWidth = isOnRoute || isHovered || isSelected ? 2.5 : 2;

            const showLabel =
              st.isTerminus ||
              st.labelPriority === "high" ||
              isHovered ||
              isSelected ||
              isOnRoute;

            return (
              <g
                key={`st-${st.name}-${st.line}`}
                className="cursor-pointer"
                onClick={() => onStationClick?.(st.nodeIds[0], st.name)}
                onMouseEnter={(e) => handleStationHover(st.name, st.line, st.nodeIds, false, e)}
                onMouseLeave={handleStationLeave}
              >
                <circle
                  cx={st.x}
                  cy={st.y}
                  r={radius}
                  fill={fillColor}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                />

                {isOrigin && (
                  <text x={st.x} y={st.y + 1} textAnchor="middle" dominantBaseline="middle" fontSize={9} fill="#000" fontWeight="800">
                    O
                  </text>
                )}
                {isDest && (
                  <text x={st.x} y={st.y + 1} textAnchor="middle" dominantBaseline="middle" fontSize={9} fill="#000" fontWeight="800">
                    D
                  </text>
                )}

                {showLabel && (
                  <text
                    x={st.labelX}
                    y={st.labelY}
                    textAnchor={st.labelAnchor}
                    fontSize={st.isTerminus || st.labelPriority === "high" ? 11 : 10}
                    fontWeight={st.isTerminus || st.labelPriority === "high" ? "700" : "400"}
                    fill={
                      isOrigin
                        ? "#4ade80"
                        : isDest
                        ? "#f87171"
                        : isOnRoute || isHovered || isSelected
                        ? "#FFFFFF"
                        : "#D0C9BE"
                    }
                    fontFamily="'Inter', system-ui, sans-serif"
                    style={{ pointerEvents: "none" }}
                  >
                    {st.name}
                  </text>
                )}
              </g>
            );
          })}

          {/* ── 4.5 Moving Train Markers (Simulated Operations) ── */}
          {trains && trains.length > 0 && trains.map((t) => {
            if (t.is_completed) return null;

            const st1 = getStationGeometry(t.current_station);
            const st2 = getStationGeometry(t.next_station);
            if (!st1) return null;

            const x2 = st2 ? st2.x : st1.x;
            const y2 = st2 ? st2.y : st1.y;

            const trainX = st1.x + (x2 - st1.x) * t.progress_pct;
            const trainY = st1.y + (y2 - st1.y) * t.progress_pct;

            const isSelected = selectedTrainId === t.train_id;
            const isHeld = t.is_held || t.status === "STOPPED";
            const lineColor = getLineColor(t.line);

            return (
              <g
                key={`train-marker-${t.train_id}`}
                transform={`translate(${trainX}, ${trainY})`}
                onClick={(e) => {
                  e.stopPropagation();
                  onTrainClick?.(t.train_id);
                }}
                className="cursor-pointer group"
              >
                {/* Outer pulsating ring for selected or held train */}
                {isSelected && (
                  <circle r={14} fill="none" stroke="#D4A017" strokeWidth={2.5} className="animate-ping opacity-75" />
                )}
                {isHeld && (
                  <circle r={12} fill="none" stroke="#E63946" strokeWidth={2} className="animate-pulse" />
                )}

                {/* Train marker pill background */}
                <rect
                  x={-16}
                  y={-9}
                  width={32}
                  height={18}
                  rx={9}
                  fill={isHeld ? "#E63946" : lineColor}
                  stroke={isSelected ? "#D4A017" : "#161B22"}
                  strokeWidth={isSelected ? 2 : 1}
                  className="transition-transform group-hover:scale-110"
                />

                {/* Train Icon / Direction text */}
                <text
                  x={0}
                  y={3}
                  fontSize={8.5}
                  fontWeight="bold"
                  fill="#FFFFFF"
                  textAnchor="middle"
                  fontFamily="'Fira Code', monospace"
                  className="pointer-events-none"
                >
                  {t.train_id}
                </text>
              </g>
            );
          })}

          {/* ── 5. Map Legend & Status Info ── */}

          <g transform="translate(40, 40)">
            <rect width={210} height={145} rx={6} fill="#161B22" opacity={0.92} stroke="#30363D" strokeWidth={1} />
            <text x={12} y={20} fontSize={11} fontWeight="700" fill="#F5F0E8" fontFamily="'Inter', system-ui, sans-serif">
              NAMMA PULSE — BENGALURU METRO
            </text>

            {CANONICAL_LINES.map((l, idx) => {
              const status = LINE_STATUS[l as keyof typeof LINE_STATUS];
              const isUnderConst = !status?.isOperational;
              return (
                <g key={`legend-${l}`} transform={`translate(12, ${38 + idx * 18})`}>
                  <line
                    x1={0} y1={0} x2={18} y2={0}
                    stroke={getLineColor(l)}
                    strokeWidth={4}
                    strokeLinecap="round"
                  />
                  <text x={26} y={4} fontSize={9.5} fill={isUnderConst ? "#8B949E" : "#D0C9BE"} fontFamily="'Inter', system-ui, sans-serif">
                    {l} Line — {status?.label}
                  </text>

                </g>
              );
            })}
          </g>
        </g>

        {/* Tooltip */}
        {tooltip && (
          <g transform={`translate(${Math.min(tooltip.x + 15, VIEW_WIDTH - 220)}, ${Math.max(tooltip.y - 50, 20)})`} style={{ pointerEvents: "none" }}>
            <rect
              width={200}
              height={tooltip.isInterchange ? 54 : 44}
              rx={6}
              fill="#161B22"
              stroke="#30363D"
              strokeWidth={1}
            />
            <rect
              x={8} y={8} width={4} height={tooltip.isInterchange ? 38 : 28}
              rx={2} fill={getLineColor(tooltip.line.split(" ")[0])}
            />
            <text x={18} y={20} fontSize={11} fontWeight="600" fill="#F5F0E8" fontFamily="'Inter', system-ui, sans-serif">
              {tooltip.name.length > 24 ? tooltip.name.slice(0, 24) + "…" : tooltip.name}
            </text>
            <text x={18} y={34} fontSize={9.5} fill="#8B949E" fontFamily="'Inter', system-ui, sans-serif">
              {tooltip.line} {tooltip.line.includes("Line") ? "" : "Line"}
            </text>
            {tooltip.isInterchange && (
              <text x={18} y={47} fontSize={8.5} fill="#D4A017" fontWeight="600" fontFamily="'Inter', system-ui, sans-serif">
                INTERCHANGE HUB
              </text>
            )}
          </g>
        )}
      </svg>
    </div>
  );
};

export default MetroMap;
