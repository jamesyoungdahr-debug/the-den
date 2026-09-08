import * as React from 'react';

export interface RingMarkProps {
  size?: number;
  /** Any brand colour; defaults to current (purple). */
  color?: string;
  /** Adds the centre dot — the first frame of the boot sequence. */
  filled?: boolean;
  style?: React.CSSProperties;
}

export declare function RingMark(props: RingMarkProps): JSX.Element;
