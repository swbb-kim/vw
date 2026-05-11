export default function Home() {
  return (
    <main
      style={{
        fontFamily: "system-ui, sans-serif",
        maxWidth: 640,
        margin: "4rem auto",
        padding: "0 1.5rem",
        lineHeight: 1.6,
      }}
    >
      <h1>Veryworth Translator</h1>
      <p>
        Telegram translation bridge for Korean &harr; Khmer. The bot endpoint
        is <code>/api/telegram</code>.
      </p>
      <p>
        To register the webhook, run:
        <br />
        <code>
          curl -X POST
          &quot;https://api.telegram.org/bot&lt;TOKEN&gt;/setWebhook?url=&lt;DEPLOY_URL&gt;/api/telegram&quot;
        </code>
      </p>
    </main>
  );
}
