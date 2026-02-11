import React, { useState } from 'react';
import { CodeBlock } from './CodeBlock';
import { TERMUX_SETUP_SCRIPT, PYTHON_BOT_SCRIPT, GITHUB_WORKFLOW_TEMPLATE, ENV_FILE_TEMPLATE, DEFAULT_STREAM_CONFIG } from '../constants';
import { StreamConfig } from '../types';
import { Terminal, Bot, Github, Save, Lock, FolderTree, FileKey, ShieldAlert } from 'lucide-react';

export const TermuxGuide: React.FC = () => {
  const [config, setConfig] = useState<StreamConfig>(DEFAULT_STREAM_CONFIG);
  const [activeTab, setActiveTab] = useState<'setup' | 'bot' | 'workflow' | 'env'>('setup');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setConfig(prev => ({ ...prev, [name]: value }));
  };

  const setupCode = TERMUX_SETUP_SCRIPT(config);
  const botCode = PYTHON_BOT_SCRIPT;
  const workflowCode = GITHUB_WORKFLOW_TEMPLATE(config);
  const envCode = ENV_FILE_TEMPLATE(config);

  return (
    <div className="max-w-6xl mx-auto p-6 h-full flex flex-col md:flex-row gap-6 animate-fade-in">
      {/* Config Panel */}
      <div className="w-full md:w-1/3 bg-gray-800 p-6 rounded-xl border border-gray-700 overflow-y-auto">
        <div className="flex items-center gap-2 mb-6 text-primary-500">
          <Save size={24} />
          <h2 className="text-xl font-bold text-white">Config Generator</h2>
        </div>
        
        <div className="bg-red-500/10 border border-red-500/30 p-3 rounded-lg mb-6 flex gap-3 items-start">
           <ShieldAlert className="text-red-400 flex-shrink-0 mt-0.5" size={16} />
           <p className="text-xs text-red-200">
             <strong>安全警告：</strong> 由于生成的脚本包含您的密钥 (Token/PAT)，请务必将 GitHub 仓库设置为 <strong>Private (私有)</strong>，不要公开！
           </p>
        </div>

        <div className="space-y-4">
          <div className="border-b border-gray-700 pb-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Github size={16} /> GitHub & Alist
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">GitHub Repo Name</label>
                <input type="text" name="githubRepo" value={config.githubRepo} onChange={handleChange} className="input-field" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">GitHub Owner</label>
                <input type="text" name="githubUser" value={config.githubUser} onChange={handleChange} className="input-field" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">GitHub PAT (Token)</label>
                <input type="password" name="githubPat" value={config.githubPat} onChange={handleChange} className="input-field" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1 flex items-center gap-1">
                   Alist Admin Password <span className="bg-blue-600 px-1 rounded text-[10px]">Auto-Set</span>
                </label>
                <input type="text" name="alistPassword" value={config.alistPassword} onChange={handleChange} className="input-field text-yellow-400" />
                <p className="text-[10px] text-gray-500 mt-1">脚本会自动将 Alist 密码修改为此值，以便 Bot 登录。</p>
              </div>
            </div>
          </div>

          <div className="border-b border-gray-700 pb-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Bot size={16} /> Telegram Bot
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Bot Token</label>
                <input type="password" name="telegramBotToken" value={config.telegramBotToken} onChange={handleChange} className="input-field" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Admin User ID</label>
                <input type="text" name="telegramAdminId" value={config.telegramAdminId} onChange={handleChange} className="input-field" />
              </div>
            </div>
          </div>

          <div>
             <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Terminal size={16} /> Stream Target
            </h3>
            <label className="block text-xs text-gray-400 mb-1">Telegram RTMP URL</label>
            <input type="text" name="telegramRtmpUrl" value={config.telegramRtmpUrl} onChange={handleChange} className="input-field" />
          </div>
        </div>
      </div>

      {/* Preview Panel */}
      <div className="w-full md:w-2/3 flex flex-col">
        <div className="flex gap-2 mb-4 bg-gray-800 p-1 rounded-lg w-fit">
          <button 
            onClick={() => setActiveTab('setup')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'setup' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            setup.sh (Deploy)
          </button>
          <button 
            onClick={() => setActiveTab('bot')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'bot' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            bot.py (Logic)
          </button>
          <button 
            onClick={() => setActiveTab('env')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'env' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            .env (Secrets)
          </button>
          <button 
            onClick={() => setActiveTab('workflow')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'workflow' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            stream.yml (Action)
          </button>
        </div>

        <div className="flex-1 overflow-auto">
          {activeTab === 'setup' && (
            <div className="space-y-2">
              <div className="bg-blue-900/20 border border-blue-900/50 p-4 rounded-lg text-sm text-blue-200">
                <p className="font-bold mb-1">部署步骤:</p>
                <ol className="list-decimal list-inside space-y-1 text-gray-300">
                  <li>在 GitHub 创建<strong>私有仓库</strong> <code>{config.githubRepo}</code></li>
                  <li>上传3个文件到 GitHub 仓库根目录 (yml文件放 <code>.github/workflows/</code>)</li>
                  <li>GitHub Secrets 添加: <code>TELEGRAM_STREAM_KEY</code></li>
                  <li>Termux 运行: <code>git clone ... && bash setup.sh</code></li>
                </ol>
              </div>
              <CodeBlock code={setupCode} language="bash" title="setup.sh" />
            </div>
          )}

          {activeTab === 'bot' && (
             <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-green-400 mb-2">
                  <FolderTree size={16} />
                  <span>功能：Alist 文件浏览 (/ls) + 自动推流</span>
                </div>
                <CodeBlock code={botCode} language="python" title="bot.py" />
             </div>
          )}

          {activeTab === 'env' && (
             <div className="space-y-2">
                <div className="bg-yellow-900/20 border border-yellow-700/50 p-4 rounded-lg text-sm text-yellow-200 flex items-start gap-3">
                  <FileKey size={20} className="flex-shrink-0" />
                  <div>
                    <p className="font-bold mb-1">关于 .env 文件</p>
                    <p className="opacity-80">
                      <code>setup.sh</code> 脚本会自动在 Termux 中生成此文件，因此您<strong>不需要</strong>手动创建它。
                      如果您想手动调试或迁移机器人，请将此内容保存为 <code>.env</code> 文件并放在 <code>bot.py</code> 同级目录。
                    </p>
                  </div>
                </div>
                <CodeBlock code={envCode} language="bash" title=".env" />
             </div>
          )}

          {activeTab === 'workflow' && (
            <div className="space-y-2">
               <CodeBlock code={workflowCode} language="yaml" title=".github/workflows/stream.yml" />
            </div>
          )}
        </div>
      </div>
      
      <style>{`
        .input-field {
          width: 100%;
          background-color: rgb(17 24 39);
          border: 1px solid rgb(55 65 81);
          border-radius: 0.375rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
          line-height: 1.25rem;
          color: white;
          transition: border-color 0.2s;
        }
        .input-field:focus {
          outline: none;
          border-color: rgb(59 130 246);
        }
      `}</style>
    </div>
  );
};
