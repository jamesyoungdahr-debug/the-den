import * as React from 'react';

export interface LockupProps {
  /** Use 'ring' whenever the mark renders below 38px. */
  mark?: 'otter' | 'ring';
  orientation?: 'horizontal' | 'stacked';
  /** Drives the wordmark size; the mark scales with it. */
  size?: number;
  /** Mono, teal, letterspaced sub-line, e.g. 'Media-first Arch'. */
  tagline?: string;
  color?: string;
  markColor?: string;
  style?: React.CSSProperties;
}

export declare function Lockup(props: LockupProps): JSX.Element;
