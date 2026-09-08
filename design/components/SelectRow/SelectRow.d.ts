import * as React from 'react';

export interface SelectRowProps {
  title?: React.ReactNode;
  /** Mono sub-line: the device path, the folder, the size. */
  meta?: React.ReactNode;
  /** Right-hand slot — usually a <StatusPill>. */
  status?: React.ReactNode;
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export declare function SelectRow(props: SelectRowProps): JSX.Element;
