'use client';

import { SCENES, type SceneConfig } from '@/lib/store-scenes';

interface SceneTabsProps {
  activeScene: string | null;
  onSelect: (sceneId: string | null) => void;
}

export function SceneTabs({ activeScene, onSelect }: SceneTabsProps) {
  const scenes = Object.values(SCENES);

  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        padding: '0 24px',
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
      }}
    >
      <TabButton
        label="全网"
        color="#333"
        isActive={activeScene === null}
        onClick={() => onSelect(null)}
      />
      {scenes.map((scene) => (
        <TabButton
          key={scene.id}
          label={scene.name}
          color={scene.primary}
          isActive={activeScene === scene.id}
          onClick={() => onSelect(scene.id)}
        />
      ))}
    </div>
  );
}

function TabButton({
  label,
  color,
  isActive,
  onClick,
}: {
  label: string;
  color: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 16px',
        borderRadius: 20,
        border: isActive ? `2px solid ${color}` : '1px solid rgba(0,0,0,0.1)',
        backgroundColor: isActive ? `${color}18` : '#fff',
        color: isActive ? color : '#666',
        fontSize: 14,
        fontWeight: isActive ? 600 : 400,
        cursor: 'pointer',
        whiteSpace: 'nowrap',
        transition: 'all 0.2s ease',
      }}
    >
      {label}
    </button>
  );
}
