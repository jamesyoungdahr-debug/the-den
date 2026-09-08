import * as React from 'react';

export interface OtterMarkProps {
  /** Rendered width in px. Below 38px use <RingMark> instead. */
  size?: number;
  /** Expression lives in the eyes only; the head never changes. */
  expression?: 'happy' | 'idle' | 'alert';
  style?: React.CSSProperties;
}

export declare function OtterMark(props: OtterMarkProps): JSX.Element;
