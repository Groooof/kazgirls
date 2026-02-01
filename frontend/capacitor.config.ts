import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.example.app',
  appName: 'stream',
  webDir: 'dist',
  server: {
    url: 'https://nex2ilo.com',
  },
  plugins: {
    CapacitorHttp: {
      enabled: true,
    },
  },
};

export default config;
