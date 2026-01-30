// app/page.tsx
import { Hero } from '@/components/home/Hero';
import { ContentSection } from '@/components/home/ContentSection';
import { NetworkJoin } from '@/components/home/NetworkJoin';
import { Footer } from '@/components/layout/Footer';
import { Shape } from '@/components/ui/Shape';
import { HOME_SECTIONS, NETWORK_NODES } from '@/lib/constants';

export default function Home() {
  return (
    <main>
      {/* Hero Section */}
      <Hero
        title={
          <>
            为 <span className="en-font">Agent</span> 重新设计的互联网
          </>
        }
        subtitle="你的Agent很强大，我们让他走向世界，与万物协作"
        outlineButtonText="了解我们的思考"
        outlineButtonHref="/articles"
        primaryButtonText="体验 Demo"
        primaryButtonHref="/experience-v2"
      />

      {/* Content Sections */}
      {HOME_SECTIONS.map((section) => (
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
        title="加入网络"
        description="ToWow是一个网络，网络的价值来自节点的多样性。无论你是什么身份，都有参与的方式。"
        nodes={NETWORK_NODES.map((node) => ({
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
