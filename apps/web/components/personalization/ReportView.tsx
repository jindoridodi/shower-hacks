import type {
  Claim,
  EvidenceExcerpt,
  Report,
} from "../../lib/personalization-types";

type ReportViewProps = {
  report?: Report;
  sources?: EvidenceExcerpt[];
  isLoading?: boolean;
  error?: string;
  isFixtureData?: boolean;
  onSourceSelect?: (sourceId: string) => void;
};

function sourceFor(sourceId: string, sources: EvidenceExcerpt[]) {
  return sources.find((source) => source.sourceId === sourceId);
}

function ClaimCard({
  claim,
  sources,
  onSourceSelect,
}: {
  claim: Claim;
  sources: EvidenceExcerpt[];
  onSourceSelect?: (sourceId: string) => void;
}) {
  return (
    <article data-claim-type={claim.claimType}>
      <p>
        <strong>{claim.claimType}</strong>
        {" · "}
        {Math.round(claim.confidence * 100)}% confidence
      </p>
      <p>{claim.text}</p>
      {claim.sourceIds.length === 0 ? (
        <p>No supporting source is available for this claim.</p>
      ) : (
        <ul aria-label="Supporting sources">
          {claim.sourceIds.map((sourceId) => {
            const source = sourceFor(sourceId, sources);

            return (
              <li key={sourceId}>
                {source ? (
                  <a
                    href={source.sourceUrl}
                    onClick={() => onSourceSelect?.(sourceId)}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Evidence: {source.sourceTitle ?? sourceId}
                  </a>
                ) : (
                  <button
                    onClick={() => onSourceSelect?.(sourceId)}
                    type="button"
                  >
                    View evidence: {sourceId}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </article>
  );
}

export function ReportView({
  report,
  sources = [],
  isLoading = false,
  error,
  isFixtureData = false,
  onSourceSelect,
}: ReportViewProps) {
  if (isLoading) {
    return (
      <section aria-busy="true" aria-labelledby="report-heading">
        <h2 id="report-heading">Evidence report</h2>
        <p>Loading source-linked claims…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section aria-labelledby="report-heading" role="alert">
        <h2 id="report-heading">Evidence report</h2>
        <p>The report could not be loaded: {error}</p>
      </section>
    );
  }

  if (!report) {
    return (
      <section aria-labelledby="report-heading">
        <h2 id="report-heading">Evidence report</h2>
        <p>No report is available for this corpus.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="report-heading">
      <h2 id="report-heading">{report.title}</h2>
      {isFixtureData ? <p>Demo fixture data</p> : null}

      {report.claims.length === 0 ? (
        <p>No factual claims can be supported by this corpus.</p>
      ) : (
        <div>
          {report.claims.map((claim) => (
            <ClaimCard
              claim={claim}
              key={claim.id}
              onSourceSelect={onSourceSelect}
              sources={sources}
            />
          ))}
        </div>
      )}

      {report.contradictions.length > 0 ? (
        <section aria-labelledby="contradictions-heading">
          <h3 id="contradictions-heading">Conflicting evidence</h3>
          <ul>
            {report.contradictions.map((contradiction) => (
              <li key={contradiction}>{contradiction}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="unknowns-heading">
        <h3 id="unknowns-heading">What the corpus does not establish</h3>
        {report.unknowns.length > 0 ? (
          <ul>
            {report.unknowns.map((unknown) => (
              <li key={unknown}>{unknown}</li>
            ))}
          </ul>
        ) : (
          <p>No additional unknowns were recorded in this report.</p>
        )}
      </section>
    </section>
  );
}
