import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: 'atl.chat docs',
    },
    links: [
      {
        text: 'Documentation',
        url: '/',
        active: 'nested-url',
      },
    ],
  };
}
