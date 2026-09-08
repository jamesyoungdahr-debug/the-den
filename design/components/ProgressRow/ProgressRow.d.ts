import * as React from 'react';

export interface ProgressRowProps {
  label?: React.ReactNode;
  percent?: number;
  /** Overrides the right-hand readout (defaults to the percentage). */
  meta?: React.ReactNode;
  tone?: 'current' | 'healthy' | 'warning';
  style?: React.CSSProperties;
}

export declare function ProgressRow(props: ProgressRowProps): JSX.Element;
