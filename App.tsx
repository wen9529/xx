import React, { useState } from 'react';
import { Terminal, Bot, Github, Save, Shield, Download, Image as ImageIcon, Video, FileText, Clipboard, Check } from 'lucide-react';
import { DEFAULT_STREAM_CONFIG, PYTHON_BOT_SCRIPT, GITHUB_WORKFLOW_TEMPLATE, GENERATE_ENV_CONTENT, SETUP_SCRIPT_CONTENT } from './constants';
import { StreamConfig } from './types';

// Inline CodeBlock Component
const CodeBlock: React.FC<{ code: string; language?: string; title?: string; filename?: string }> = ({ code, language = 'bash', title, filename }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!filename) return;
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700 my-4 shadow-lg">
      <div className="flex justify-between items-center px-4 py-2 bg-gray-700/50 border-b border-gray-700">
        <span className="text-xs font-mono text-gray-300 uppercase">{title || language}</span>
        <div className="flex gap-2">
          {filename && (
            <button onClick={handleDownload} className="p-1 text-gray-400 hover:text-blue-400 transition-colors" title={`Download ${filename}`}>
              <Download size={16} />
            </button>
          )}
          <button onClick={handleCopy} className="p-1 text-gray-400 hover:text-white transition-colors" title="Copy code">
            {copied ? <Check size={16} className="text-green-400" /> : <Clipboard size={16} />}
          </button>
        </div>
      </div>
      <div className="p-4 overflow-x-auto">
        <pre className="font-mono text-sm text-gray-200 whitespace-pre">{code}</pre>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  const [config, setConfig] = useState<StreamConfig>(DEFAULT_STREAM_CONFIG);
  const [activeTab, setActiveTab] = useState<'bot' | 'workflow' | 'env' | 'setup'>('setup');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setConfig(prev => ({ ...prev, [name]: value }));
  };

  const botCode = PYTHON_BOT_SCRIPT;
  const workflowCode = GITHUB_WORKFLOW_TEMPLATE(config);
  const envCode = GENERATE_ENV_CONTENT(config);
  const setupCode = SETUP_SCRIPT_CONTENT;

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white font-sans">
        {/* Header */}
      <header className="h-16 border-b border-gray-800 bg-gray-900 flex items-center justify-between px-6 flex-shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Terminal className="text-white h-5 w-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white">
            StreamForge <span className="text-gray-500 font-normal">| Deployment Kit</span>
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-gray-900 relative p-6">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row gap-6">
        
          {/* Config Panel */}
          <div className="w-full lg:w-1/3 bg-gray-800 p-6 rounded-xl border border-gray-700 h-fit">
            <div className="flex items-center gap-2 mb-6 text-blue-400">
              <Save size={20} />
              <h2 className="font-bold text-white">Configuration</h2>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-gray-400 uppercase font-semibold">GitHub</label>
                <input name="githubUser" placeholder="Owner (e.g., myname)" value={config.githubUser} onChange={handleChange} className="input-field" />
                <input name="githubRepo" placeholder="Repo (e.g., stream-repo)" value={config.githubRepo} onChange={handleChange} className="input-field" />
                <input name="githubPat" type="password" placeholder="PAT (ghp_...)" value={config.githubPat} onChange={handleChange} className="input-field" />
              </div>

              <div className="space-y-2 pt-4 border-t border-gray-700">
                <label className="text-xs text-gray-400 uppercase font-semibold">Telegram</label>
                <input name="telegramBotToken" type="password" placeholder="Bot Token" value={config.telegramBotToken} onChange={handleChange} className="input-field" />
                <input name="telegramAdminId" placeholder="Admin ID (Numeric)" value={config.telegramAdminId} onChange={handleChange} className="input-field" />
                <input name="telegramRtmpUrl" placeholder="RTMP URL" value={config.telegramRtmpUrl} onChange={handleChange} className="input-field" />
              </div>

              <div className="space-y-2 pt-4 border-t border-gray-700">
                <label className="text-xs text-gray-400 uppercase font-semibold flex items-center gap-2"><ImageIcon size={12}/> Audio Stream Cover</label>
                <input name="defaultCoverUrl" placeholder="https://..." value={config.defaultCoverUrl} onChange={handleChange} className="input-field text-xs" />
              </div>

              <div className="space-y-2 pt-2">
                <label className="text-xs text-gray-400 uppercase font-semibold flex items-center gap-2"><Video size={12}/> Max Bitrate</label>
                <input name="videoBitrate" placeholder="6000k" value={config.videoBitrate} onChange={handleChange} className="input-field" />
                <p className="text-[10px] text-gray-500">Affects FFmpeg encoding quality (default: 6000k).</p>
              </div>

              <div className="mt-4 p-3 bg-blue-900/20 border border-blue-900/50 rounded text-xs text-blue-200">
                <Shield size={14} className="inline mr-1"/>
                Data remains local.
              </div>
            </div>
          </div>

          {/* Output Panel */}
          <div className="w-full lg:w-2/3 flex flex-col bg-gray-800 rounded-xl border border-gray-700 overflow-hidden min-h-[600px]">
            <div className="flex border-b border-gray-700 bg-gray-900/50 overflow-x-auto">
              <button onClick={() => setActiveTab('setup')} className={`tab-btn ${activeTab === 'setup' ? 'active' : ''}`}>
                <Terminal size={16} /> setup.sh
              </button>
              <button onClick={() => setActiveTab('env')} className={`tab-btn ${activeTab === 'env' ? 'active' : ''}`}>
                <FileText size={16} /> .env
              </button>
              <button onClick={() => setActiveTab('bot')} className={`tab-btn ${activeTab === 'bot' ? 'active' : ''}`}>
                <Bot size={16} /> bot.py
              </button>
              <button onClick={() => setActiveTab('workflow')} className={`tab-btn ${activeTab === 'workflow' ? 'active' : ''}`}>
                <Github size={16} /> stream.yml
              </button>
            </div>

            <div className="flex-1 p-0 overflow-auto bg-[#1e1e1e]">
              {activeTab === 'setup' && (
                <div className="p-6">
                    <div className="mb-4 text-sm text-gray-400">
                      <b>Installation Script:</b> Save as <code>setup.sh</code> and run <code>bash setup.sh</code> in Termux.
                    </div>
                    <CodeBlock code={setupCode} language="bash" filename="setup.sh" />
                </div>
              )}
              {activeTab === 'bot' && (
                <div className="p-6">
                    <div className="mb-4 text-sm text-gray-400">
                      Main logic. Browses Alist files and triggers GitHub Actions.
                    </div>
                    <CodeBlock code={botCode} language="python" filename="bot.py" />
                </div>
              )}
              {activeTab === 'env' && (
                <div className="p-6">
                    <div className="mb-4 text-sm text-gray-400">
                      <b>Variables File:</b> Copy this content to <code>$HOME/.env</code>.
                    </div>
                    <CodeBlock code={envCode} language="bash" filename=".env" />
                </div>
              )}
              {activeTab === 'workflow' && (
                <div className="p-6">
                    <div className="mb-4 text-sm text-gray-400">
                      Upload to <code>.github/workflows/stream.yml</code> in your repo.
                    </div>
                    <CodeBlock code={workflowCode} language="yaml" filename="stream.yml" />
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <style>{`
        .input-field {
          width: 100%;
          background: #111827;
          border: 1px solid #374151;
          color: white;
          padding: 8px;
          border-radius: 4px;
          font-size: 13px;
        }
        .input-field:focus {
          border-color: #3b82f6;
          outline: none;
        }
        .tab-btn {
          min-width: 100px;
          padding: 16px;
          font-size: 14px;
          font-weight: 500;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          color: #9ca3af;
          transition: all 0.2s;
          white-space: nowrap;
        }
        .tab-btn:hover { color: white; background: rgba(255,255,255,0.05); }
        .tab-btn.active {
          background: #1f2937;
          color: #3b82f6;
          border-top: 2px solid #3b82f6;
        }
      `}</style>
    </div>
  );
};

export default App;
