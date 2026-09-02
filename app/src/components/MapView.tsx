import { useEffect, useRef } from "react";
import L from "leaflet";
import { MapContainer, Marker, TileLayer, ZoomControl, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import type { CandidateResult } from "../types";

interface MapViewProps {
  candidates: CandidateResult[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function MapView({ candidates, selectedId, onSelect }: MapViewProps) {
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
        <BoundsController candidates={candidates} />
        <SelectionController candidates={candidates} selectedId={selectedId} />
        {candidates.map((candidate) => (
          <Marker
            key={candidate.id}
            position={[candidate.location.latitude, candidate.location.longitude]}
            icon={scoreIcon(candidate, candidate.id === selectedId)}
            title={`${candidate.name}: score ${candidate.overall_score.toFixed(1)}`}
            alt={candidate.name}
            eventHandlers={{ click: () => onSelect(candidate.id) }}
          />
        ))}
      </MapContainer>
      <div className="map-vignette" aria-hidden="true" />
      <div className="scan-line" aria-hidden="true" />
      <div className="map-feed-label" aria-hidden="true">
        MAP FEED / OSM
      </div>
    </section>
  );
}

function BoundsController({ candidates }: { candidates: CandidateResult[] }) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.latLngBounds(
      candidates.map(({ location }) => [location.latitude, location.longitude]),
    );
    map.fitBounds(bounds, { padding: [90, 90], maxZoom: 11, animate: false });
  }, [candidates, map]);
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
  const state = candidate.hard_constraints.passed ? "valid" : "excluded";
  const score = Math.round(candidate.overall_score);
  return L.divIcon({
    className: "score-marker-shell",
    html: `<span class="score-marker ${state}${selected ? " selected" : ""}"><b>${score}</b><i>${candidate.rank}</i></span>`,
    iconSize: [58, 58],
    iconAnchor: [29, 29],
  });
}
