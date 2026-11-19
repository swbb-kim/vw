import RunwayML, { TaskFailedError, TaskTimedOutError } from "@runwayml/sdk";

// Runway Dev text-to-image. Docs: https://docs.dev.runwayml.com/api.md
// `gen4_image` accepts a prompt with no reference images; `ratio` values are
// model-specific, so check /api.md before changing either. Pricing lives only
// at https://docs.dev.runwayml.com/guides/pricing.md.
const MODEL = "gen4_image" as const;
const RATIO = "1280:720" as const;
const MAX_PROMPT = 1000;

export function runwayConfigured(): boolean {
  return Boolean(process.env.RUNWAYML_API_SECRET);
}

// The SDK reads RUNWAYML_API_SECRET from the environment.
let client: RunwayML | undefined;
function getClient(): RunwayML {
  client ??= new RunwayML();
  return client;
}

export async function generateImage(
  prompt: string,
  timeoutMs: number,
): Promise<string> {
  const task = await getClient()
    .textToImage.create({
      model: MODEL,
      promptText: prompt.slice(0, MAX_PROMPT),
      ratio: RATIO,
    })
    .waitForTaskOutput({ timeout: timeoutMs });

  const url = task.output?.[0];
  if (!url) throw new Error("Runway task succeeded without output");
  return url; // Temporary URL: hand it off (e.g. to Telegram) right away.
}

export function formatRunwayError(err: unknown): string {
  if (err instanceof TaskFailedError) {
    const d = err.taskDetails as { failure?: string; failureCode?: string };
    return `⚠️ 이미지 생성 실패: ${d.failure ?? "unknown"}${
      d.failureCode ? ` (${d.failureCode})` : ""
    }`;
  }
  if (err instanceof TaskTimedOutError) {
    return "⚠️ 이미지 생성 시간이 초과되었습니다. 잠시 후 다시 시도하세요.";
  }
  if (err instanceof RunwayML.AuthenticationError) {
    return "⚠️ RUNWAYML_API_SECRET 인증 실패. Vercel 환경변수를 확인하세요.";
  }
  if (err instanceof RunwayML.APIError) {
    return `⚠️ Runway API 오류 (${err.status}): ${err.message.slice(0, 200)}`;
  }
  const message = err instanceof Error ? err.message : String(err);
  return `⚠️ 이미지 생성 실패: ${message.slice(0, 200)}`;
}
