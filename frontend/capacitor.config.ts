import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.example.app',
  appName: 'stream',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
