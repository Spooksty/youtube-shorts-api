export type JobStatus =
  | "waiting"
  | "postponed"
  | "running"
  | "pending_review"
  | "approved"
  | "rejected"
  | "published"
  | "error";

export interface Schedule {
  videos_per_day: number;
  publish_times: string[];
  auto_publish: boolean;
}

export interface Channel {
  id: number;
  name: string;
  niche: string;
  audience_age: string;
  language: string;
  voice_id: string;
  style: string;
  is_active: boolean;
  linked: boolean;
  youtube_channel_id: string | null;
  topic_count: number;
  published: number;
  pending: number;
  schedule: Schedule | null;
}

export interface Topic {
  id: number;
  title: string;
  description: string;
  is_active: boolean;
}

export interface Template {
  id: number;
  name: string;
  body: string;
  version: number;
  is_active: boolean;
}

export interface JobRow {
  id: number;
  status: JobStatus;
  channel_id: number;
  channel: string;
  topic: string | null;
  title: string | null;
  duration: number | null;
  current_step: string | null;
  error: string | null;
  manual: boolean;
  created_at: string;
  finished_at: string | null;
}

export interface LogRow {
  id: number;
  job_id: number;
  step: string;
  result: "ok" | "warn" | "retry" | "error" | "info";
  message: string;
  started_at: string;
  duration_ms: number;
  channel?: string;
}

export interface VideoDetail extends JobRow {
  publish_after: string | null;
  video: {
    title: string;
    description: string;
    tags: string[];
    url: string;
    duration: number;
    width: number;
    height: number;
    has_audio: boolean;
    check_passed: boolean;
    script_id: number;
  } | null;
  scripts: {
    id: number;
    attempt: number;
    text: string;
    title: string;
    keywords: string[];
    is_valid: boolean;
    validation_message: string | null;
  }[];
  media: {
    id: number;
    kind: string;
    provider: string;
    keyword: string | null;
    author: string | null;
    source_url: string | null;
    file: string;
  }[];
  costs: { service: string; operation: string; units: number; cost_eur: number; simulated: boolean }[];
  total_cost: number;
  publication: { youtube_video_id: string; published_at: string; privacy: string; ai_generated: boolean } | null;
  logs: LogRow[];
}

export interface Notification {
  id: number;
  level: "info" | "warning" | "error";
  message: string;
  job_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface Budget {
  spent: number;
  limit: number;
  pct: number;
}

export interface Providers {
  llm: string;
  tts: string;
  media: string;
  platform: string;
}
