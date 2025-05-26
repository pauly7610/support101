interface ImportMetaEnv {
  readonly VITE_WS_URL?: string;
  // add other env vars as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
