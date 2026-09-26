import type {
  CommunicationDraft,
  EvidenceExcerpt,
  Report,
  TimelineItem,
} from "./personalization-types";

export type PersonalizationData = {
  report: Report;
  sources: EvidenceExcerpt[];
  timeline: TimelineItem[];
  draft: CommunicationDraft;
};

export function usesFixtures(): boolean {
  return process.env.NEXT_PUBLIC_USE_FIXTURES !== "false";
}

export async function loadPersonalizationData(): Promise<PersonalizationData> {
  if (!usesFixtures()) {
    throw new Error(
      "Live personalization adapter is not available. Set NEXT_PUBLIC_USE_FIXTURES=true to use fixture data.",
    );
  }

  const [report, sources, timeline, draft] = await Promise.all([
    import("../../../data/fixtures/report.json").then((m) => m.default as Report),
    import("../../../data/fixtures/evidence-excerpts.json").then(
      (m) => m.default as EvidenceExcerpt[],
    ),
    import("../../../data/fixtures/timeline.json").then(
      (m) => m.default as TimelineItem[],
    ),
    import("../../../data/fixtures/communication-draft.json").then(
      (m) => m.default as CommunicationDraft,
    ),
  ]);

  return { report, sources, timeline, draft };
}
