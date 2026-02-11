export enum AppView {
  TERMUX_GUIDE = 'TERMUX_GUIDE',
  WORKFLOW_GENERATOR = 'WORKFLOW_GENERATOR',
  AI_ASSISTANT = 'AI_ASSISTANT',
}

export interface StreamConfig {
  // GitHub Repo Details
  githubUser: string;
  githubRepo: string;
  githubPat: string; // Personal Access Token (for Bot to trigger Action)
  
  // Telegram Configuration
  telegramBotToken: string;
  telegramAdminId: string; // Your User ID (to prevent others from using your bot)
  telegramRtmpUrl: string;
  telegramStreamKey: string;

  // File Defaults
  fileName: string;
  fileUrl: string;
}

export interface Message {
  id: string;
  role: 'user' | 'model';
  content: string;
  timestamp: number;
}
