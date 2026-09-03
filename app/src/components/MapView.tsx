import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, Marker, TileLayer, ZoomControl, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import { pinSizeForField, planLabels, samePlan } from "../lib/field";
import type { FieldPlan, LabelSide } from "../lib/field";
import { fitColour, fitScale, pinSizeForZoom } from "../lib/pins";
import type { CandidateResult, ConstraintStatus, RouteBoundary } from "../types";

// The search boundary is the one vector besides the pins: a dotted purple line with a whisper of fill.
const BOUNDARY_STYLE = {
  color: "#a78bfa", weight: 4, opacity: 1, dashArray: "1 9", lineCap: "round" as const,
  fillColor: "#a78bfa", fillOpacity: 0.05, className: "search-boundary",
};

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
  /** Rendered over the map, inside its bounds: the place card. */
  overlay?: ReactNode;
}

export function MapView({ candidates, fieldKey, routeBoundary, selectedId, onSelect, overlay }: MapViewProps) {
  const first = candidates[0].location;
  // Pin size and which pins carry a name are planned from the screen, so a crowded run stays legible.
  const [plan, setPlan] = useState<FieldPlan>({ size: pinSizeForZoom(9), labelled: new Map(candidates.map((candidate) => [candidate.id, "right"])) });
  const adoptPlan = useCallback((next: FieldPlan) => setPlan((current) => (samePlan(current, next) ? current : next)), []);
  // Pins within limits are graded green against the whole run: the best fit is the most vivid.
  const fit = fitScale(candidates.map((candidate) => candidate.overall_score));
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
            key={routeBoundary.retrieved_at}
            data={routeBoundary.geometry}
            interactive={false}
            style={BOUNDARY_STYLE}
          />
        )}
        <FieldController
          candidates={candidates}
          fieldKey={fieldKey}
          routeBoundary={routeBoundary}
          selectedId={selectedId}
        />
        <FieldPlanner candidates={candidates} selectedId={selectedId} onPlan={adoptPlan} />
        {candidates.map((candidate) => {
          const selected = candidate.id === selectedId;
          return (
            <Marker
              key={candidate.id}
              position={[candidate.location.latitude, candidate.location.longitude]}
              icon={scoreIcon(candidate, selected, plan.size, fit(candidate.overall_score), plan.labelled.get(candidate.id))}
              zIndexOffset={selected ? 1000 : 0}
              title={`${candidate.name}: rank ${candidate.rank}, score ${candidate.overall_score.toFixed(1)}, ${MARKER_TEXT[candidate.hard_constraints.status]}`}
              alt={`${candidate.name}, ${MARKER_TEXT[candidate.hard_constraints.status]}`}
              eventHandlers={{ click: () => onSelect(candidate.id) }}
            />
          );
        })}
      </MapContainer>
      {overlay}
      <ul className="map-legend" aria-label="Map key">
        <li><i className="legend-pin valid" aria-hidden="true" />Within limits, greener fits better</li>
        <li><i className="legend-pin unverified" aria-hidden="true" />Limit unverified</li>
        <li><i className="legend-pin excluded" aria-hidden="true" />Outside limit</li>
        <li><i className="legend-line" aria-hidden="true" />Search area</li>
      </ul>
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
    map.fitBounds(bounds, { ...visibleFieldPadding(map.getSize().x), maxZoom: 14, animate: false });
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
  // On a phone the header floats over the top of the map, so the fit keeps the field below it.
  if (width <= 760) return { paddingTopLeft: [36, 112], paddingBottomRight: [36, 36] };
  const rankWidth = width <= 1050 ? 270 : 310;
  const dossierWidth = width <= 1050 ? 370 : 420;
  return { paddingTopLeft: [rankWidth + 50, 190], paddingBottomRight: [dossierWidth + 50, 70] };
}

/**
 * Projects the field onto the screen after every move and zoom and hands back
 * the pin size and the set of pins whose names fit without colliding.
 */
function FieldPlanner({
  candidates,
  selectedId,
  onPlan,
}: {
  candidates: CandidateResult[];
  selectedId: string;
  onPlan: (plan: FieldPlan) => void;
}) {
  const map = useMap();
  const replan = useCallback(() => {
    const pins = candidates.map((candidate) => {
      const point = map.latLngToContainerPoint([candidate.location.latitude, candidate.location.longitude]);
      return { id: candidate.id, x: point.x, y: point.y, name: candidate.name, rank: candidate.rank };
    });
    const size = pinSizeForField(map.getZoom(), pins);
    onPlan({ size, labelled: planLabels(pins, size, selectedId) });
  }, [candidates, map, onPlan, selectedId]);
  useMapEvents({ moveend: replan, zoomend: replan });
  useEffect(replan, [replan]);
  return null;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
}

function scoreIcon(candidate: CandidateResult, selected: boolean, size: number, fit: number, label: LabelSide | undefined): L.DivIcon {
  const state = MARKER_STATE[candidate.hard_constraints.status];
  const score = Math.round(candidate.overall_score);
  const half = size / 2;
  return L.divIcon({
    className: "score-marker-shell",
    html: `<span class="score-marker ${state}${selected ? " selected" : ""}" style="--pin:${size}px;--fit:${fit.toFixed(2)};--fit-colour:${fitColour(fit)}"><b>${score}</b><i>${candidate.rank}</i></span>`
      + (label ? `<span class="pin-label ${label}" aria-hidden="true">${escapeHtml(candidate.name)}</span>` : ""),
    iconSize: [size, size],
    iconAnchor: [half, half],
  });
}
