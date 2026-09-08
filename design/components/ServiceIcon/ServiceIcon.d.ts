import * as React from 'react';

export interface ServiceIconProps {
  service?: 'plex' | 'sonarr' | 'radarr' | 'prowlarr' | 'qbit' | 'zfs' | 'podman' | 'plasma';
  /** Tile edge in px; the squircle radius scales with it. */
  size?: number;
  /** Optional mono caption under the tile. */
  label?: string;
  style?: React.CSSProperties;
}

export declare function ServiceIcon(props: ServiceIconProps): JSX.Element;
