import * as React from 'react';

export interface ButtonProps {
  children?: React.ReactNode;
  /** primary = purple, the only shouting colour. Never teal — teal means healthy. */
  variant?: 'primary' | 'secondary' | 'quiet' | 'onCurrent';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export declare function Button(props: ButtonProps): JSX.Element;
