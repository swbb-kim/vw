import Anthropic from "@anthropic-ai/sdk";
import { after } from "next/server";
import { formatRunwayError, generateImage, runwayConfigured } from "../../lib/runway";

export const runtime = "nodejs";
// Image generation runs after the webhook is acknowledged (see `after` below),
// but still counts against the function's max duration.
export const maxDuration = 60;
const IMAGE_TIMEOUT_MS = 50_000;

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const TG_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const WEBHOOK_SECRET = process.env.TELEGRAM_WEBHOOK_SECRET;
const MODEL = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-6";

const ALLOWED_CHAT_IDS = (process.env.ALLOWED_CHAT_IDS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean)
  .map(Number)
  .filter((n) => Number.isFinite(n));

const SYSTEM_PROMPT = `당신은 한국 본사와 캄보디아 현장 직원 사이의 실시간 통역사입니다. 베리워즈(Veryworth)라는 회사의 비즈니스 커뮤니케이션을 번역합니다.

규칙:
1. 입력이 한국어면 → 자연스러운 크메르어(ភាសាខ្មែរ)로 번역
2. 입력이 크메르어면 → 자연스러운 한국어로 번역
3. 입력이 영어면 → 한국어와 크메르어 둘 다 번역
4. 번역 결과만 출력. "번역:", 인용부호, 부연설명 모두 금지
5. 업무용 톤 유지. 명령은 명령답게, 질문은 질문답게
6. 회사명·사람 이름·지명 같은 고유명사는 원문 그대로 유지
7. 숫자·날짜·금액은 정확하게 보존
8. 영어 입력일 때만 두 언어 동시 출력 형식:
🇰🇭 [크메르어]
🇰🇷 [한국어]`;

type TelegramMessage = {
  message_id: number;
  text?: string;
  from?: { is_bot?: boolean };
  chat: { id: number; type: string };
};

type TelegramUpdate = {
  message?: TelegramMessage;
  edited_message?: TelegramMessage;
};

async function sendTelegram(
  chatId: number,
  text: string,
  replyTo?: number,
): Promise<void> {
  if (!TG_TOKEN) return;
  const res = await fetch(
    `https://api.telegram.org/bot${TG_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        reply_to_message_id: replyTo,
      }),
    },
  );
  if (!res.ok) {
    console.error("Telegram send failed:", res.status, await res.text());
  }
}

async function sendTelegramPhoto(
  chatId: number,
  photoUrl: string,
  caption: string,
  replyTo?: number,
): Promise<void> {
  if (!TG_TOKEN) return;
  const res = await fetch(`https://api.telegram.org/bot${TG_TOKEN}/sendPhoto`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      photo: photoUrl,
      caption: caption.slice(0, 1024),
      reply_to_message_id: replyTo,
    }),
  });
  if (!res.ok) {
    console.error("Telegram sendPhoto failed:", res.status, await res.text());
  }
}

// Matches "/image prompt" and "/image@YourBot prompt". Returns the prompt
// (possibly empty) or null when the message is not an /image command.
function parseImageCommand(text: string): string | null {
  const m = text.trim().match(/^\/image(?:@\w+)?(?:\s+([\s\S]*))?$/i);
  return m ? (m[1] ?? "").trim() : null;
}

async function handleImage(msg: TelegramMessage, prompt: string): Promise<void> {
  if (!runwayConfigured()) {
    await sendTelegram(
      msg.chat.id,
      "⚠️ RUNWAYML_API_SECRET이 설정되지 않았습니다.",
      msg.message_id,
    );
    return;
  }
  if (!prompt) {
    await sendTelegram(
      msg.chat.id,
      "사용법: /image <설명>  (예: /image 앙코르와트 일출, 수채화 스타일)",
      msg.message_id,
    );
    return;
  }
  await sendTelegram(msg.chat.id, "🎨 이미지 생성 중...", msg.message_id);
  try {
    const url = await generateImage(prompt, IMAGE_TIMEOUT_MS);
    await sendTelegramPhoto(msg.chat.id, url, prompt, msg.message_id);
  } catch (err) {
    console.error("Runway error:", err);
    await sendTelegram(msg.chat.id, formatRunwayError(err), msg.message_id);
  }
}

function shouldSkip(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 2) return true;
  // Skip messages with no letters (emoji-only, numbers-only, punctuation-only)
  if (!/\p{Letter}/u.test(trimmed)) return true;
  // Skip bot commands like /start, /help
  if (trimmed.startsWith("/")) return true;
  return false;
}

function formatError(err: unknown): string {
  if (err instanceof Anthropic.AuthenticationError) {
    return "⚠️ ANTHROPIC_API_KEY 인증 실패. Vercel 환경변수를 확인하세요.";
  }
  if (err instanceof Anthropic.NotFoundError) {
    return `⚠️ 모델 '${MODEL}'을 찾을 수 없습니다. ANTHROPIC_MODEL 환경변수를 확인하세요.`;
  }
  if (err instanceof Anthropic.PermissionDeniedError) {
    return `⚠️ API 키 권한 부족: 모델 '${MODEL}'에 접근할 수 없습니다.`;
  }
  if (err instanceof Anthropic.RateLimitError) {
    return "⚠️ API 호출 한도 초과. 잠시 후 다시 시도하세요.";
  }
  if (err instanceof Anthropic.BadRequestError) {
    return `⚠️ 요청 오류 (400): ${err.message.slice(0, 200)}`;
  }
  if (err instanceof Anthropic.APIError) {
    return `⚠️ API 오류 (${err.status}): ${err.message.slice(0, 200)}`;
  }
  const message = err instanceof Error ? err.message : String(err);
  return `⚠️ 번역 실패: ${message.slice(0, 200)}`;
}

async function translate(input: string): Promise<string> {
  const reply = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1500,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: input }],
  });

  const textBlock = reply.content.find((b) => b.type === "text");
  return textBlock && textBlock.type === "text" ? textBlock.text.trim() : "";
}

export async function POST(req: Request): Promise<Response> {
  // Verify webhook secret if configured
  if (WEBHOOK_SECRET) {
    const got = req.headers.get("x-telegram-bot-api-secret-token");
    if (got !== WEBHOOK_SECRET) {
      return new Response("unauthorized", { status: 401 });
    }
  }

  let update: TelegramUpdate;
  try {
    update = (await req.json()) as TelegramUpdate;
  } catch {
    return new Response("bad json", { status: 400 });
  }

  const msg = update.message ?? update.edited_message;
  if (!msg?.text) return new Response("ok");

  // Allowlist enforcement (must be set for safety)
  if (ALLOWED_CHAT_IDS.length === 0) {
    console.warn("ALLOWED_CHAT_IDS not configured — ignoring all messages");
    return new Response("ok");
  }
  if (!ALLOWED_CHAT_IDS.includes(msg.chat.id)) {
    return new Response("ok");
  }

  // Anti-loop: ignore bot messages
  if (msg.from?.is_bot) return new Response("ok");

  // /image <prompt>: generate with Runway after acknowledging the webhook,
  // so Telegram doesn't time out and redeliver while the task runs.
  const imagePrompt = parseImageCommand(msg.text);
  if (imagePrompt !== null) {
    if (update.message) after(() => handleImage(msg, imagePrompt));
    return new Response("ok");
  }

  // Cost filter
  if (shouldSkip(msg.text)) return new Response("ok");

  try {
    const translated = await translate(msg.text);
    if (translated) {
      await sendTelegram(msg.chat.id, translated, msg.message_id);
    }
  } catch (err) {
    console.error("Translation error:", err);
    await sendTelegram(msg.chat.id, formatError(err), msg.message_id);
  }

  return new Response("ok");
}

export async function GET(): Promise<Response> {
  return new Response(
    JSON.stringify({
      ok: true,
      bot: "veryworth-translator",
      model: MODEL,
      allowlist_size: ALLOWED_CHAT_IDS.length,
      webhook_secret_configured: Boolean(WEBHOOK_SECRET),
      anthropic_key_configured: Boolean(process.env.ANTHROPIC_API_KEY),
      telegram_token_configured: Boolean(TG_TOKEN),
      runway_key_configured: runwayConfigured(),
    }),
    { headers: { "Content-Type": "application/json" } },
  );
}
