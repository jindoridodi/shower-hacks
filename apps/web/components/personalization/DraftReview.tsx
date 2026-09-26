"use client";

import { useState } from "react";

import type {
  CommunicationDraft,
  EvidenceExcerpt,
} from "../../lib/personalization-types";

type DraftReviewProps = {
  draft?: CommunicationDraft;
  sources?: EvidenceExcerpt[];
  isLoading?: boolean;
  error?: string;
  isFixtureData?: boolean;
  onSourceSelect?: (sourceId: string) => void;
};

function sourceFor(sourceId: string, sources: EvidenceExcerpt[]) {
  return sources.find((source) => source.sourceId === sourceId);
}

export function DraftReview({
  draft,
  sources = [],
  isLoading = false,
  error,
  isFixtureData = false,
  onSourceSelect,
}: DraftReviewProps) {
  const [recipient, setRecipient] = useState(draft?.recipient ?? "");
  const [subject, setSubject] = useState(draft?.subject ?? "");
  const [body, setBody] = useState(draft?.body ?? "");

  if (isLoading) {
    return (
      <section aria-busy="true" aria-labelledby="draft-review-heading">
        <h2 id="draft-review-heading">Draft review</h2>
        <p>Preparing the source-linked draft…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section aria-labelledby="draft-review-heading" role="alert">
        <h2 id="draft-review-heading">Draft review</h2>
        <p>The draft could not be loaded: {error}</p>
      </section>
    );
  }

  if (!draft) {
    return (
      <section aria-labelledby="draft-review-heading">
        <h2 id="draft-review-heading">Draft review</h2>
        <p>No source-linked draft is available for this corpus.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="draft-review-heading">
      <h2 id="draft-review-heading">Draft review</h2>
      {isFixtureData ? <p>Demo fixture data</p> : null}
      <p role="status">
        <strong>{draft.label}</strong>
      </p>
      {draft.reviewRequired ? (
        <p>This draft requires human review before it can be used.</p>
      ) : null}

      <div>
        <label htmlFor="draft-recipient">Recipient</label>
        <input
          id="draft-recipient"
          onChange={(event) => setRecipient(event.target.value)}
          type="text"
          value={recipient}
        />
      </div>

      <div>
        <label htmlFor="draft-subject">Subject</label>
        <input
          id="draft-subject"
          onChange={(event) => setSubject(event.target.value)}
          type="text"
          value={subject}
        />
      </div>

      <div>
        <label htmlFor="draft-body">Draft</label>
        <textarea
          id="draft-body"
          onChange={(event) => setBody(event.target.value)}
          rows={10}
          value={body}
        />
      </div>

      <section aria-labelledby="draft-sources-heading">
        <h3 id="draft-sources-heading">Public sources</h3>
        <ul>
          {draft.sourceIds.map((sourceId) => {
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
                    {source.sourceTitle ?? sourceId}
                  </a>
                ) : (
                  <button
                    onClick={() => onSourceSelect?.(sourceId)}
                    type="button"
                  >
                    View source: {sourceId}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <p>This interface does not send, post, or email the draft.</p>
    </section>
  );
}
