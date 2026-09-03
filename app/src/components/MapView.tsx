import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, Marker, TileLayer, ZoomControl, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import { focusMask } from "../lib/focusMask";
import { pinSizeForZoom } from "../lib/pins";
import type { CandidateResult, ConstraintStatus, RouteBoundary } from "../types";

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
        {routeBoundary && (
          <GeoJSON
            key={`mask:${routeBoundary.retrieved_at}`}
            data={focusMask(routeBoundary.geometry)}
            interactive={false}
            style={{ stroke: false, fillColor: "#0d1416", fillOpacity: 0.46, fillRule: "evenodd", className: "focus-mask" }}
          />
        )}
        {routeBoundary && (
          <GeoJSON
            key={routeBoundary.retrieved_at}
            data={routeBoundary.geometry}
            interactive={false}
            style={{ color: "#2f8f3c", weight: 2.5, opacity: 0.85, fillColor: "#5cc463", fillOpacity: 0.07, dashArray: "8 7" }}
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
      <div className="map-vignette" aria-hidden="true" />
    </section>
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
