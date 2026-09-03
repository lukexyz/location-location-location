import { STATUS_BADGE, cardFacts, photoUrl } from "../lib/placeCard";
import type { CandidateResult } from "../types";

interface Props {
  candidate: CandidateResult;
  /** Folder the bundle's photos resolve against; undefined when there is none. */
  assetBase: string | undefined;
  /** What-if score to show instead of the researched one while a preview is active. */
  previewScore?: number;
  onClose: () => void;
  onEvidence: () => void;
}

/**
 * The card that pops open when a place is picked: its photo with the author and
 * licence in the corner, the rank, the hard-limit badge, three small facts, and
 * a way into the evidence. A place without a photo gets a soft gradient and the
 * same facts, so an imported file with no reachable images still works.
 */
export function PlaceCard({ candidate, assetBase, previewScore, onClose, onEvidence }: Props) {
  const photo = candidate.photo;
  const src = photoUrl(assetBase, photo);
  const status = candidate.hard_constraints.status;
  const facts = cardFacts(candidate);
  const score = previewScore ?? candidate.overall_score;
  return (
    <section className={`place-card ${status}`} aria-labelledby="place-card-name" data-testid="place-card">
      <div className={`place-card-photo ${src ? "" : "no-photo"}`}>
        {src && photo && (
          <img
            src={src}
            alt={`${photo.title}. Photo by ${photo.author}, ${photo.licence}.`}
            width={photo.width}
            height={photo.height}
            loading="lazy"
            decoding="async"
          />
        )}
        <span className="place-card-rank" aria-label={`Rank ${candidate.rank}`}>{candidate.rank}</span>
        <span className={`place-card-badge ${status}`}>{STATUS_BADGE[status]}</span>
        {/* A label, not a heading: the evidence panel already carries the place's heading. */}
        <span id="place-card-name" className="place-card-name">{candidate.name}</span>
        {photo && (
          <a className="place-card-credit" href={photo.source_url} target="_blank" rel="noreferrer" title={`${photo.title} on Wikimedia Commons`}>
            {photo.author} · {photo.licence}
          </a>
        )}
        <button className="place-card-close" type="button" aria-label="Close card" onClick={onClose}>×</button>
      </div>
      <dl className="place-card-facts">
        <div className="place-card-score">
          <dt>{previewScore !== undefined ? "What-if fit" : "Fit"}</dt>
          <dd>{score.toFixed(1)}</dd>
        </div>
        {facts.map((fact) => (
          <div key={fact.key}>
            <dt>{fact.label}</dt>
            <dd>{fact.value}</dd>
          </div>
        ))}
      </dl>
      <button className="place-card-evidence" type="button" onClick={onEvidence}>
        See the evidence <span aria-hidden="true">→</span>
      </button>
    </section>
  );
}
