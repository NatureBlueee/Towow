// components/ui/Shape.tsx
import styles from './Shape.module.css';

interface ShapePosition {
  top?: string | number;
  left?: string | number;
  right?: string | number;
  bottom?: string | number;
}

interface ShapeProps {
  type: 'circle' | 'square' | 'triangle';
  size: number;
  color: string;
  position: ShapePosition;
  animation?: 'float' | 'pulse' | 'spin';
  animationDuration?: string;
  animationDelay?: string;
  opacity?: number;
  blur?: number;
  rotate?: number;
  mixBlendMode?: string;
  border?: string;
  className?: string;
}

export function Shape({
  type,
  size,
  color,
  position,
  animation,
  animationDuration,
  animationDelay,
  opacity = 1,
  blur,
  rotate,
  mixBlendMode,
  border,
  className,
}: ShapeProps) {
  // Build position style
  const positionStyle: React.CSSProperties = {};
  if (position.top !== undefined) positionStyle.top = typeof position.top === 'number' ? `${position.top}px` : position.top;
  if (position.left !== undefined) positionStyle.left = typeof position.left === 'number' ? `${position.left}px` : position.left;
  if (position.right !== undefined) positionStyle.right = typeof position.right === 'number' ? `${position.right}px` : position.right;
  if (position.bottom !== undefined) positionStyle.bottom = typeof position.bottom === 'number' ? `${position.bottom}px` : position.bottom;

  // Build animation style
  const animationStyle: React.CSSProperties = {};
  if (animation) {
    animationStyle.animationName = animation;
    animationStyle.animationIterationCount = 'infinite';
    animationStyle.animationTimingFunction = animation === 'spin' ? 'linear' : 'ease-in-out';
  }
  if (animationDuration) animationStyle.animationDuration = animationDuration;
  if (animationDelay) animationStyle.animationDelay = animationDelay;

  // Build transform style
  const transforms: string[] = [];
  if (rotate) transforms.push(`rotate(${rotate}deg)`);

  // Build filter style
  const filters: string[] = [];
  if (blur) filters.push(`blur(${blur}px)`);

  // Triangle uses border technique
  if (type === 'triangle') {
    const triangleHeight = size * 0.866; // equilateral triangle height ratio
    const halfSize = size / 2;

    const triangleStyle: React.CSSProperties = {
      ...positionStyle,
      ...animationStyle,
      width: 0,
      height: 0,
      borderStyle: 'solid',
      borderLeftWidth: `${halfSize}px`,
      borderRightWidth: `${halfSize}px`,
      borderBottomWidth: `${triangleHeight}px`,
      borderLeftColor: 'transparent',
      borderRightColor: 'transparent',
      borderBottomColor: border ? 'transparent' : color,
      borderTopWidth: 0,
      borderTopColor: 'transparent',
      opacity,
      ...(transforms.length > 0 && { transform: transforms.join(' ') }),
      ...(filters.length > 0 && { filter: filters.join(' ') }),
      ...(mixBlendMode && { mixBlendMode: mixBlendMode as React.CSSProperties['mixBlendMode'] }),
    };

    // For hollow triangle, we need a different approach
    if (border) {
      triangleStyle.borderLeftColor = 'transparent';
      triangleStyle.borderRightColor = 'transparent';
      triangleStyle.borderBottomColor = color;
    }

    return (
      <div
        className={`${styles.shape} ${className || ''}`}
        style={triangleStyle}
      />
    );
  }

  // Circle and Square
  const shapeStyle: React.CSSProperties = {
    ...positionStyle,
    ...animationStyle,
    width: `${size}px`,
    height: `${size}px`,
    opacity,
    ...(transforms.length > 0 && { transform: transforms.join(' ') }),
    ...(filters.length > 0 && { filter: filters.join(' ') }),
    ...(mixBlendMode && { mixBlendMode: mixBlendMode as React.CSSProperties['mixBlendMode'] }),
  };

  // Apply background or border based on whether it's hollow
  if (border) {
    shapeStyle.border = border;
    shapeStyle.background = 'transparent';
  } else {
    shapeStyle.background = color;
  }

  const shapeClass = type === 'circle' ? styles.circle : styles.square;

  return (
    <div
      className={`${styles.shape} ${shapeClass} ${className || ''}`}
      style={shapeStyle}
    />
  );
}
