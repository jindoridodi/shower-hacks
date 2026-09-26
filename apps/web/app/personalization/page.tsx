"use client";

import { useEffect, useState } from "react";

import { DraftReview } from "../../components/personalization/DraftReview";
import { ReportView } from "../../components/personalization/ReportView";
import { Timeline } from "../../components/personalization/Timeline";
import {
  loadPersonalizationData,
  usesFixtures,
  type PersonalizationData,
} from "../../lib/personalization-fixtures";

export default function PersonalizationPage() {
  const [data, setData] = useState<PersonalizationData>();
  const [error, setError] = useState<string>();
  const [selectedSourceId, setSelectedSourceId] = useState<string>();

  useEffect(() => {
    loadPersonalizationData().then(setData).catch((loadError: unknown) => {
      setError(
        loadError instanceof Error ? loadError.message : "Unknown loading error.",
      );
    });
  }, []);

  const selectedSource = data?.sources.find(
    (source) => source.sourceId === selectedSourceId,
  );
  const isLoading = !data && !error;

  return (
    <main>
      <h1>Personalization</h1>
      {usesFixtures() ? <p>Demo fixture mode</p> : null}

      {selectedSource ? (
        <aside aria-label="Selected evidence">
          <h2>{selectedSource.sourceTitle ?? selectedSource.sourceId}</h2>
          <p>{selectedSource.text}</p>
          <a href={selectedSource.sourceUrl} rel="noreferrer" target="_blank">
            Open public source
          </a>
        </aside>
      ) : null}

      <ReportView
        error={error}
        isFixtureData={usesFixtures()}
        isLoading={isLoading}
        onSourceSelect={setSelectedSourceId}
        report={data?.report}
        sources={data?.sources}
      />
      <Timeline
        error={error}
        isFixtureData={usesFixtures()}
        isLoading={isLoading}
        items={data?.timeline}
        onSourceSelect={setSelectedSourceId}
        sources={data?.sources}
      />
      <DraftReview
        draft={data?.draft}
        error={error}
        isFixtureData={usesFixtures()}
        isLoading={isLoading}
        onSourceSelect={setSelectedSourceId}
        sources={data?.sources}
      />
    </main>
  );
}
