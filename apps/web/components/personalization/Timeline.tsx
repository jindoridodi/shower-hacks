import type {
  EvidenceExcerpt,
  TimelineItem,
} from "../../lib/personalization-types";

type TimelineProps = {
  items?: TimelineItem[];
  sources?: EvidenceExcerpt[];
  isLoading?: boolean;
  error?: string;
  isFixtureData?: boolean;
  onSourceSelect?: (sourceId: string) => void;
};

function sourceFor(item: TimelineItem, sources: EvidenceExcerpt[]) {
  return sources.find((source) => source.sourceId === item.sourceId);
}

function TimelineRow({
  item,
  sources,
  onSourceSelect,
}: {
  item: TimelineItem;
  sources: EvidenceExcerpt[];
  onSourceSelect?: (sourceId: string) => void;
}) {
  const source = sourceFor(item, sources);

  return (
    <li>
      <p>
        <strong>{item.dateText}</strong>
        {" · "}
        {Math.round(item.confidence * 100)}% confidence
      </p>
      <p>{item.eventText}</p>
      {source ? (
        <a
          href={source.sourceUrl}
          onClick={() => onSourceSelect?.(item.sourceId)}
          rel="noreferrer"
          target="_blank"
        >
          Source: {source.sourceTitle ?? item.sourceId}
        </a>
      ) : (
        <button onClick={() => onSourceSelect?.(item.sourceId)} type="button">
          View source: {item.sourceId}
        </button>
      )}
    </li>
  );
}

export function Timeline({
  items = [],
  sources = [],
  isLoading = false,
  error,
  isFixtureData = false,
  onSourceSelect,
}: TimelineProps) {
  if (isLoading) {
    return (
      <section aria-busy="true" aria-labelledby="timeline-heading">
        <h2 id="timeline-heading">Public timeline</h2>
        <p>Loading explicitly published dates…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section aria-labelledby="timeline-heading" role="alert">
        <h2 id="timeline-heading">Public timeline</h2>
        <p>Timeline data could not be loaded: {error}</p>
      </section>
    );
  }

  const datedItems = items
    .filter((item) => item.normalizedDate)
    .sort((left, right) =>
      left.normalizedDate!.localeCompare(right.normalizedDate!),
    );
  const impreciseItems = items.filter((item) => !item.normalizedDate);

  return (
    <section aria-labelledby="timeline-heading">
      <h2 id="timeline-heading">Public timeline</h2>
      {isFixtureData ? <p>Demo fixture data</p> : null}

      {items.length === 0 ? (
        <p>No explicitly dated public events were found in this corpus.</p>
      ) : null}

      {datedItems.length > 0 ? (
        <ol>
          {datedItems.map((item) => (
            <TimelineRow
              item={item}
              key={`${item.sourceId}-${item.normalizedDate}`}
              onSourceSelect={onSourceSelect}
              sources={sources}
            />
          ))}
        </ol>
      ) : null}

      {impreciseItems.length > 0 ? (
        <section aria-labelledby="imprecise-dates-heading">
          <h3 id="imprecise-dates-heading">Dates without precise ordering</h3>
          <p>These source dates are shown as published and are not placed on the chronological timeline.</p>
          <ul>
            {impreciseItems.map((item) => (
              <TimelineRow
                item={item}
                key={`${item.sourceId}-${item.dateText}`}
                onSourceSelect={onSourceSelect}
                sources={sources}
              />
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
