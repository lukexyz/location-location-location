import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, Marker, TileLayer, ZoomControl, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import { focusMask } from "../lib/focusMask";
import { pinSizeForZoom } from "../lib/pins";
import type { CandidateResult, ConstraintStatus, RouteBoundary } from "../types";

// Outside the boundary the map is desaturated rather than darkened, so it stays bright. Two grey layers
// feathered by different amounts (see FocusFilters) blend with the tiles' saturation; a faint white fog
// on the far layer lifts the outside a touch more.
const FOCUS_LAYERS: ReadonlyArray<{ layer: string; fillColor: string; fillOpacity: number }> = [
  { layer: "near", fillColor: "#8a8a8a", fillOpacity: 0.85 },
  { layer: "far", fillColor: "#8a8a8a", fillOpacity: 0.75 },
  { layer: "fog far", fillColor: "#ffffff", fillOpacity: 0.16 },
];

const MARKER_STATE: Record<ConstraintStatus, string> = { pass: "valid", unknown: "unverified", fail: "excluded" };
const MARKER_TEXT: Record<ConstraintStatus, string> = {
  pass: "within limits", unknown: "limit unverified", fail: "outside hard limit",
};

interface MapViewProps {
  /** Candidates in bundle order; sorting the register must not move the map. */
  candidates: CandidateResult[];
  /** Changes only when a different bundle is loaded, which is the only time the map refits. */
  fieldKey: string;
  routeBoundary?: RouteBoundary;
  selectedId: string;
  onSelect: (id: string) => void;
}

export function MapView({ candidates, fieldKey, routeBoundary, selectedId, onSelect }: MapViewProps) {
  const first = candidates[0].location;
  const [zoom, setZoom] = useState(9);
  const pinSize = pinSizeForZoom(zoom);
  return (
    <section className="map-field" aria-label="Candidate map">
      <MapContainer
        center={[first.latitude, first.longitude]}
        zoom={9}
        zoomControl={false}
        className="map-canvas"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ZoomControl position="bottomright" />
        {routeBoundary && FOCUS_LAYERS.map(({ layer, fillColor, fillOpacity }) => (
          <GeoJSON
            key={`mask:${layer}:${routeBoundary.retrieved_at}`}
            data={focusMask(routeBoundary.geometry)}
            interactive={false}
            style={{ stroke: false, fillColor, fillOpacity, fillRule: "evenodd", className: `focus-mask ${layer}` }}
          />
        ))}
        {routeBoundary && (
          <GeoJSON
            key={routeBoundary.retrieved_at}
            data={routeBoundary.geometry}
            interactive={false}
            style={{ color: "#2f8f3c", weight: 2, opacity: 0.7, fillColor: "#5cc463", fillOpacity: 0.06, dashArray: "8 7" }}
          />
        )}
        <FieldController
          candidates={candidates}
          fieldKey={fieldKey}
          routeBoundary={routeBoundary}
          selectedId={selectedId}
        />
        <ZoomTracker onZoom={setZoom} />
        {candidates.map((candidate) => {
          const selected = candidate.id === selectedId;
          return (
            <Marker
              key={candidate.id}
              position={[candidate.location.latitude, candidate.location.longitude]}
              icon={scoreIcon(candidate, selected, pinSize)}
              zIndexOffset={selected ? 1000 : 0}
              title={`${candidate.name}: rank ${candidate.rank}, score ${candidate.overall_score.toFixed(1)}, ${MARKER_TEXT[candidate.hard_constraints.status]}`}
              alt={`${candidate.name}, ${MARKER_TEXT[candidate.hard_constraints.status]}`}
              eventHandlers={{ click: () => onSelect(candidate.id) }}
            />
          );
        })}
      </MapContainer>
      <FocusFilters />
    </section>
  );
}

/**
 * The mask is eroded before it is blurred, which pushes the hole outward by the
 * erosion radius, so the dimming starts at the boundary line and fades away from
 * it; nothing inside the search is touched. Radii are in screen pixels and the
 * phone variants are smaller because the boundary is.
 */
function FocusFilters() {
  const filters: Array<[string, number, number]> = [
    ["focus-near", 20, 10], ["focus-far", 70, 35], ["focus-near-phone", 10, 5], ["focus-far-phone", 32, 16],
  ];
  return (
    <svg className="focus-filters" aria-hidden="true" focusable="false" width="0" height="0">
      <defs>
        {filters.map(([id, erode, blur]) => (
          <filter key={id} id={id} x="-5%" y="-5%" width="110%" height="110%" colorInterpolationFilters="sRGB">
            <feMorphology operator="erode" radius={erode} />
            <feGaussianBlur stdDeviation={blur} />
          </filter>
        ))}
      </defs>
    </svg>
  );
}

/**
 * Fits the whole field once per bundle and flies only to a selection the user
 * made. Sorting, what-if sliders, and the initial top-ranked selection never
 * move the map, so a pan or zoom survives every control change.
 */
function FieldController({
  candidates,
  fieldKey,
  routeBoundary,
  selectedId,
}: {
  candidates: CandidateResult[];
  fieldKey: string;
  routeBoundary?: RouteBoundary;
  selectedId: string;
}) {
  const map = useMap();
  const latest = useRef({ candidates, routeBoundary, selectedId });
  latest.current = { candidates, routeBoundary, selectedId };
  const settledSelection = useRef(selectedId);

  useEffect(() => {
    const { candidates: field, routeBoundary: boundary, selectedId: initial } = latest.current;
    const bounds = L.latLngBounds(field.map(({ location }) => [location.latitude, location.longitude]));
    if (boundary) bounds.extend(L.geoJSON(boundary.geometry).getBounds());
    map.fitBounds(bounds, { ...visibleFieldPadding(map.getSize().x), maxZoom: 11, animate: false });
    // The bundle's own top candidate is selected on load; that is not a user choice.
    settledSelection.current = initial;
  }, [fieldKey, map]);

  useEffect(() => {
    if (settledSelection.current === selectedId) return;
    settledSelection.current = selectedId;
    const selected = latest.current.candidates.find((candidate) => candidate.id === selectedId);
    if (selected) {
      map.flyTo([selected.location.latitude, selected.location.longitude], Math.max(map.getZoom(), 10), {
        duration: 0.7,
      });
    }
  }, [map, selectedId]);
  return null;
}

/**
 * On a wide screen the side panels, the header, and the front door float over
 * the map, so the field is fitted into the part that stays visible. On a
 * phone the map has the width to itself.
 */
export function visibleFieldPadding(width: number): { paddingTopLeft: [number, number]; paddingBottomRight: [number, number] } {
  if (width <= 760) return { paddingTopLeft: [36, 36], paddingBottomRight: [36, 36] };
  const rankWidth = width <= 1050 ? 270 : 310;
  const dossierWidth = width <= 1050 ? 370 : 420;
  return { paddingTopLeft: [rankWidth + 50, 190], paddingBottomRight: [dossierWidth + 50, 70] };
}

function ZoomTracker({ onZoom }: { onZoom: (zoom: number) => void }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) });
  useEffect(() => onZoom(map.getZoom()), [map, onZoom]);
  return null;
}

function scoreIcon(candidate: CandidateResult, selected: boolean, size: number): L.DivIcon {
  const state = MARKER_STATE[candidate.hard_constraints.status];
  const score = Math.round(candidate.overall_score);
  const half = size / 2;
  return L.divIcon({
    className: "score-marker-shell",
    html: `<span class="score-marker ${state}${selected ? " selected" : ""}" style="--pin:${size}px"><b>${score}</b><i>${candidate.rank}</i></span>`,
    iconSize: [size, size],
    iconAnchor: [half, half],
  });
}
