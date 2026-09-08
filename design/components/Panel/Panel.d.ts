import * as React from 'react';

export interface PanelProps {
  children?: React.ReactNode;
  /** Mono, letterspaced, uppercase eyebrow. */
  title?: React.ReactNode;
  /** Right-aligned mono metadata — a StatusPill fits here. */
  meta?: React.ReactNode;
  tone?: 'surface' | 'deep' | 'raised';
  padding?: number;
  style?: React.CSSProperties;
}

export declare function Panel(props: PanelProps): JSX.Element;
