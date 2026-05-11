export const metadata = {
  title: "Veryworth Translator Bot",
  description: "Telegram translation bridge: Korean <-> Khmer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
