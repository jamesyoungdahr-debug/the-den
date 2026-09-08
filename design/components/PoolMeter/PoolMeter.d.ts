import * as React from 'react';

export interface PoolMeterProps {
  percent?: number;
  size?: number;
  /** healthy (teal) is the default state; warning is amber. */
  tone?: 'healthy' | 'warning' | 'idle';
  /** Mono detail lines beside the ring, e.g. ['2.9 TB used','mirror · 2 disks']. */
  lines?: string[];
  style?: React.CSSProperties;
}

export declare function PoolMeter(props: PoolMeterProps): JSX.Element;
