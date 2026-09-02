import { useEffect, useRef } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, Marker, TileLayer, ZoomControl, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import type { CandidateResult, ConstraintStatus, RouteBoundary } from "../types";

const MARKER_STATE: Record<ConstraintStatus, string> = { pass: "valid", unknown: "unverified", fail: "excluded" };
const MARKER_TEXT: Record<ConstraintStatus, string> = {
  pass: "within limits", unknown: "limit unverified", fail: "outside hard limit",
};

interface MapViewProps {
  candidates: CandidateResult[];
  routeBoundary?: RouteBoundary;
  selectedId: string;
  onSelect: (id: string) => void;
}

export function MapView({ candidates, routeBoundary, selectedId, onSelect }: MapViewProps) {
  const first = candidates[0].location;
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
            style={{ color: "#b6ff73", weight: 2, opacity: 0.72, fillOpacity: 0.045, dashArray: "7 6" }}
          />
        )}
        <BoundsController candidates={candidates} routeBoundary={routeBoundary} />
        <SelectionController candidates={candidates} selectedId={selectedId} />
        {candidates.map((candidate) => (
          <Marker
            key={candidate.id}
            position={[candidate.location.latitude, candidate.location.longitude]}
            icon={scoreIcon(candidate, candidate.id === selectedId)}
            title={`${candidate.name}: score ${candidate.overall_score.toFixed(1)}, ${MARKER_TEXT[candidate.hard_constraints.status]}`}
            alt={candidate.name}
            eventHandlers={{ click: () => onSelect(candidate.id) }}
          />
        ))}
      </MapContainer>
      <div className="map-vignette" aria-hidden="true" />
      <div
        key={`${selectedId}:${routeBoundary?.retrieved_at ?? "no-boundary"}`}
        className="scan-line active"
        aria-hidden="true"
      />
      <div className="map-feed-label" aria-hidden="true">
        MAP FEED / OSM {routeBoundary ? `/ LIMIT ${routeBoundary.provider.toUpperCase()}` : ""}
      </div>
    </section>
  );
}

function BoundsController({
  candidates,
  routeBoundary,
}: {
  candidates: CandidateResult[];
  routeBoundary?: RouteBoundary;
}) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.latLngBounds(
      candidates.map(({ location }) => [location.latitude, location.longitude]),
    );
    if (routeBoundary) bounds.extend(L.geoJSON(routeBoundary.geometry).getBounds());
    map.fitBounds(bounds, { padding: [90, 90], maxZoom: 11, animate: false });
  }, [candidates, map, routeBoundary]);
  return null;
}

function SelectionController({
  candidates,
  selectedId,
}: {
  candidates: CandidateResult[];
  selectedId: string;
}) {
  const map = useMap();
  const previousSelection = useRef(selectedId);
  useEffect(() => {
    if (previousSelection.current === selectedId) return;
    previousSelection.current = selectedId;
    const selected = candidates.find((candidate) => candidate.id === selectedId);
    if (selected) {
      map.flyTo([selected.location.latitude, selected.location.longitude], Math.max(map.getZoom(), 10), {
        duration: 0.7,
      });
    }
  }, [candidates, map, selectedId]);
  return null;
}

function scoreIcon(candidate: CandidateResult, selected: boolean): L.DivIcon {
  const state = MARKER_STATE[candidate.hard_constraints.status];
  const score = Math.round(candidate.overall_score);
  return L.divIcon({
    className: "score-marker-shell",
    html: `<span class="score-marker ${state}${selected ? " selected" : ""}"><b>${score}</b><i>${candidate.rank}</i></span>`,
    iconSize: [58, 58],
    iconAnchor: [29, 29],
  });
}
