/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MOCK?: string;
  readonly VITE_API_URL?: string;
  readonly VITE_PUBLIC_URL?: string;
  readonly VITE_EVENTS_HTTP_DOMAIN?: string;
  readonly VITE_EVENTS_REALTIME_DOMAIN?: string;
  readonly VITE_EVENTS_API_KEY?: string;
}
