
export interface StreamConfig {
  // GitHub Repo Details
  githubUser: string;
  githubRepo: string;
  githubPat: string; // Personal Access Token
  
  // Telegram Configuration
  telegramBotToken: string;
  telegramAdminId: string;
  telegramRtmpUrl: string;
  telegramStreamKey: string;

  // Alist Configuration
  alistPassword: string;
  alistPublicUrl: string; // New: Public domain for Alist (e.g., via Cloudflare)
  aria2Secret: string; // New: For offline download security

  // Cloudflare
  cloudflaredToken: string; // New: Tunnel token

  // File Defaults
  fileName: string;
  fileUrl: string;

  // Stream Settings
  defaultCoverUrl: string; // Custom cover for audio files
  videoBitrate: string;    // e.g., "6000k"
}