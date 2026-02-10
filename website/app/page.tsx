// app/page.tsx
import { getTranslations, getLocale } from 'next-intl/server';
import { Hero } from '@/components/home/Hero';
import { SecondMeLogin } from '@/components/home/SecondMeLogin';
import { ContentSection } from '@/components/home/ContentSection';
import { NetworkJoin } from '@/components/home/NetworkJoin';
import { Footer } from '@/components/layout/Footer';
import { Shape } from '@/components/ui/Shape';
import { getHomeSections, getNetworkNodes } from '@/lib/home-data';

export default async function Home() {
  const t = await getTranslations('Home');
  const locale = await getLocale();
  const sections = getHomeSections(locale);
  const nodes = getNetworkNodes(locale);

  return (
    <main>
      {/* Hero Section */}
      <Hero
        title={
          <>
            {t.rich('heroTitle', {
              agent: (chunks) => <span className="en-font">{chunks}</span>,
            })}
          </>
        }
        subtitle={t('heroSubtitle')}
        outlineButtonText={t('outlineButton')}
        outlineButtonHref="/articles"
        primaryButtonText={t('primaryButton')}
        primaryButtonHref="/articles/join-us"
        secondaryButtonText={t('secondaryButton')}
        secondaryButtonHref="/store/"
      />

      {/* SecondMe Login */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: '-40px', marginBottom: '40px', position: 'relative', zIndex: 20 }}>
        <SecondMeLogin />
      </div>

      {/* Content Sections */}
      {sections.map((section) => (
        <ContentSection
          key={section.id}
          gridColumn={section.gridColumn}
          title={section.title}
          content={section.content}
          linkText={section.linkText}
          linkHref={section.linkHref}
          textAlign={section.textAlign}
        >
          {section.shapes.map((shape, index) => (
            <Shape
              key={index}
              type={shape.type}
              size={shape.size}
              color={shape.color}
              position={shape.position}
              opacity={shape.opacity}
              animation={shape.animation}
              animationDuration={shape.animationDuration}
              mixBlendMode={shape.mixBlendMode}
              rotate={shape.rotate}
              border={shape.border}
            />
          ))}
        </ContentSection>
      ))}

      {/* Network Join Section */}
      <NetworkJoin
        id="join-network"
        title={t('joinNetworkTitle')}
        description={t('joinNetworkDesc')}
        nodes={nodes.map((node) => ({
          icon: <i className={node.icon} />,
          label: node.label,
          position: node.position,
          backgroundColor: node.backgroundColor,
          textColor: node.textColor,
          shape: node.shape,
          animationDuration: node.animationDuration,
          animationDelay: node.animationDelay,
        }))}
      />

      {/* Footer */}
      <Footer variant="home" />
    </main>
  );
}
