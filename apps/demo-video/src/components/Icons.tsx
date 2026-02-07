import type React from 'react';

interface IconProps {
  size?: number;
  color?: string;
  strokeWidth?: number;
  style?: React.CSSProperties;
}

const defaults = { size: 16, color: '#ffffff', strokeWidth: 2 };

const svgBase = (size: number, label: string, children: React.ReactNode): React.ReactElement => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-label={label}
  >
    <title>{label}</title>
    {children}
  </svg>
);

export const SparklesIcon: React.FC<IconProps> = ({
  size = defaults.size,
  color = defaults.color,
}) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'Sparkles',
      <>
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
        <path d="M5 3v4" />
        <path d="M19 17v4" />
        <path d="M3 5h4" />
        <path d="M17 19h4" />
      </>,
    )}
  </span>
);

export const BotIcon: React.FC<IconProps> = ({ size = defaults.size, color = defaults.color }) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'Bot',
      <>
        <path d="M12 8V4H8" />
        <rect width="16" height="12" x="4" y="8" rx="2" />
        <path d="M2 14h2" />
        <path d="M20 14h2" />
        <path d="M15 13v2" />
        <path d="M9 13v2" />
      </>,
    )}
  </span>
);

export const UserIcon: React.FC<IconProps> = ({ size = defaults.size, color = defaults.color }) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'User',
      <>
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </>,
    )}
  </span>
);

export const MessageCircleIcon: React.FC<IconProps> = ({
  size = defaults.size,
  color = defaults.color,
}) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(size, 'Message', <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />)}
  </span>
);

export const CopyIcon: React.FC<IconProps> = ({ size = defaults.size, color = defaults.color }) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'Copy',
      <>
        <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
      </>,
    )}
  </span>
);

export const CheckIcon: React.FC<IconProps> = ({
  size = defaults.size,
  color = defaults.color,
}) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(size, 'Check', <path d="M20 6 9 17l-5-5" />)}
  </span>
);

export const ExternalLinkIcon: React.FC<IconProps> = ({
  size = defaults.size,
  color = defaults.color,
}) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'External link',
      <>
        <path d="M15 3h6v6" />
        <path d="M10 14 21 3" />
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      </>,
    )}
  </span>
);

export const SearchIcon: React.FC<IconProps> = ({
  size = defaults.size,
  color = defaults.color,
}) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'Search',
      <>
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </>,
    )}
  </span>
);

export const SendIcon: React.FC<IconProps> = ({ size = defaults.size, color = defaults.color }) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'Send',
      <>
        <path d="m22 2-7 20-4-9-9-4Z" />
        <path d="M22 2 11 13" />
      </>,
    )}
  </span>
);

export const ShieldCheckIcon: React.FC<IconProps> = ({
  size = defaults.size,
  color = defaults.color,
}) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'Verified source',
      <>
        <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
        <path d="m9 12 2 2 4-4" />
      </>,
    )}
  </span>
);

export const FileTextIcon: React.FC<IconProps> = ({
  size = defaults.size,
  color = defaults.color,
}) => (
  <span style={{ color, display: 'inline-flex' }}>
    {svgBase(
      size,
      'Document',
      <>
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <path d="M10 9H8" />
        <path d="M16 13H8" />
        <path d="M16 17H8" />
      </>,
    )}
  </span>
);
