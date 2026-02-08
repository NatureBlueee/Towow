import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';
import { NoiseTexture } from '@/components/layout/NoiseTexture';
import { ScrollGradientBackground } from '@/components/ui/ScrollGradientBackground';
import "./globals.css";

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export const metadata: Metadata = {
  title: "ToWow - Geometric Garden",
  description: "为 Agent 重新设计的互联网",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} data-locale={locale}>
      <head>
        <link
          rel="preconnect"
          href="https://assets-persist.lovart.ai"
          crossOrigin="anonymous"
        />
        <link
          rel="preload"
          href="https://cdnjs.cloudflare.com/ajax/libs/remixicon/4.6.0/remixicon.min.css"
          as="style"
        />
        <link
          href="https://cdnjs.cloudflare.com/ajax/libs/remixicon/4.6.0/remixicon.min.css"
          rel="stylesheet"
        />
      </head>
      <body>
        <ScrollGradientBackground />
        <NoiseTexture />
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
