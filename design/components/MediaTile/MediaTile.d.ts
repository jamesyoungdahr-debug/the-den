import * as React from 'react';

export interface MediaTileProps {
  title?: React.ReactNode;
  meta?: React.ReactNode;
  width?: number;
  /** Height = width × ratio. 1.48 is the poster default. */
  ratio?: number;
  /** Stripe colour of the placeholder ground. */
  tone?: 'current' | 'healthy';
  /** Real artwork URL; replaces the placeholder. */
  art?: string;
  style?: React.CSSProperties;
}

export declare function MediaTile(props: MediaTileProps): JSX.Element;
