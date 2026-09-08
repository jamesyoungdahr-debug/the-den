import * as React from 'react';

export interface OtterFullProps {
  /** Rendered width in px. Full body is for wallpapers, empty states and stickers — never UI chrome. */
  size?: number;
  pose?: 'sitting' | 'standing';
  /** Passed straight through to the head. */
  expression?: 'happy' | 'idle' | 'alert';
  style?: React.CSSProperties;
}

export declare function OtterFull(props: OtterFullProps): JSX.Element;
