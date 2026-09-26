export type Claim = {
  id: string;
  text: string;
  claimType: "observed" | "inferred" | "uncertain";
  confidence: number;
  sourceIds: string[];
};

export type Report = {
  id: string;
  title: string;
  claims: Claim[];
  contradictions: string[];
  unknowns: string[];
  generatedAt: string;
};

export type EvidenceExcerpt = {
  sourceId: string;
  sourceTitle?: string;
  sourceUrl: string;
  text: string;
  sensitivityStatus: string;
};

export type TimelineItem = {
  dateText: string;
  normalizedDate?: string;
  eventText: string;
  sourceId: string;
  confidence: number;
};

export type CommunicationDraft = {
  label: string;
  recipient: string;
  subject: string;
  body: string;
  sourceIds: string[];
  reviewRequired: boolean;
};
