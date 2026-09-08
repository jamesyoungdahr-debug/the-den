import * as React from 'react';

export interface StatusPillProps {
  children?: React.ReactNode;
  /** healthy is the only teal in the system. */
  tone?: 'healthy' | 'working' | 'warning' | 'idle';
  /** Wrap in a surface chip instead of running inline. */
  solid?: boolean;
  style?: React.CSSProperties;
}

export declare function StatusPill(props: StatusPillProps): JSX.Element;
