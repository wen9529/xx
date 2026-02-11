import React, { useState } from 'react';
import { CodeBlock } from './CodeBlock';
import { TERMUX_SETUP_SCRIPT, PYTHON_BOT_SCRIPT, GITHUB_WORKFLOW_TEMPLATE, ENV_FILE_TEMPLATE, DEFAULT_STREAM_CONFIG } from '../constants';
import { StreamConfig } from '../types';
import { Terminal, Bot, Github, Save, FolderTree, ShieldAlert, DownloadCloud, Activity, AlertTriangle, FileText } from 'lucide-react';

export const TermuxGuide: React.FC = () => {
  const [config, setConfig] = useState<StreamConfig>(DEFAULT_STREAM_CONFIG);
  const [activeTab, setActiveTab] = useState<'setup' | 'bot' | 'workflow' | 'env'>('setup');
  const [showDirectInstall, setShowDirectInstall] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setConfig(prev => ({ ...prev, [name]: value }));
  };

  const setupCode = TERMUX_SETUP_SCRIPT(config);
  const botCode = PYTHON_BOT_SCRIPT;
  const workflowCode = GITHUB_WORKFLOW_TEMPLATE(config);
  const envCode = ENV_FILE_TEMPLATE(config);

  // Helper to generate a 'cat' command for direct pasting
  const directInstallCmd = `cat << 'EOF' > setup.sh
${setupCode}
EOF
chmod +x setup.sh
bash setup.sh`;

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
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Alist Password</label>
                  <input type="text" name="alistPassword" value={config.alistPassword} onChange={handleChange} className="input-field text-yellow-400" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Aria2 Secret</label>
                  <input type="text" name="aria2Secret" value={config.aria2Secret} onChange={handleChange} className="input-field text-green-400" />
                </div>
              </div>
              <p className="text-[10px] text-gray-500">部署后请在 Alist 后台->设置->Aria2 中填入此 RPC Secret。</p>
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
            bot.py (Source)
          </button>
          <button 
            onClick={() => setActiveTab('env')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'env' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            .env
          </button>
          <button 
            onClick={() => setActiveTab('workflow')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'workflow' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
          >
            stream.yml
          </button>
        </div>

        <div className="flex-1 overflow-auto">
          {activeTab === 'setup' && (
            <div className="space-y-4">
              {/* Troubleshooting Box */}
              <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 rounded-lg flex gap-3 items-start">
                <AlertTriangle className="text-yellow-400 flex-shrink-0 mt-1" size={20} />
                <div className="text-sm text-gray-300">
                  <h4 className="font-bold text-yellow-200 mb-1">遇到 "No such file or directory" 错误?</h4>
                  <p className="mb-2">这说明 <code>git clone</code> 后，仓库是空的。请尝试以下修复方法：</p>
                  <ul className="list-disc list-inside space-y-1 text-xs text-gray-400">
                    <li><strong>方法 1 (推荐):</strong> 点击代码块右上角的 <DownloadCloud className="inline w-3 h-3"/> 按钮下载文件，然后手动上传到 GitHub。</li>
                    <li><strong>方法 2 (直接生成):</strong> 在 Termux 中输入 <code>cat &gt; setup.sh</code>，粘贴下方代码，按 <code>Ctrl+D</code> 保存。</li>
                    <li><strong>方法 3 (无Git模式):</strong> 点击下方 "切换到: 直接粘贴命令" 按钮，一键生成文件。</li>
                  </ul>
                </div>
              </div>

              <div className="flex justify-between items-center">
                 <div className="text-sm font-bold text-blue-300">部署脚本内容:</div>
                 <button 
                   onClick={() => setShowDirectInstall(!showDirectInstall)}
                   className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded text-white transition-colors"
                 >
                   {showDirectInstall ? "切换回: 源码预览" : "切换到: 直接安装命令 (无Git)"}
                 </button>
              </div>

              {showDirectInstall ? (
                 <div className="animate-fade-in">
                    <p className="text-xs text-gray-400 mb-2">复制以下所有内容直接粘贴到 Termux，将自动创建文件并运行：</p>
                    <CodeBlock code={directInstallCmd} language="bash" title="Direct Install Command" />
                 </div>
              ) : (
                <CodeBlock code={setupCode} language="bash" title="setup.sh" filename="setup.sh" />
              )}
            </div>
          )}

          {activeTab === 'bot' && (
             <div className="space-y-2">
                <div className="flex items-center gap-4 text-sm mb-2">
                   <div className="flex items-center gap-1 text-green-400"><DownloadCloud size={16}/> <span>下载: /download</span></div>
                   <div className="flex items-center gap-1 text-blue-400"><FolderTree size={16}/> <span>浏览: /ls</span></div>
                   <div className="flex items-center gap-1 text-purple-400"><Activity size={16}/> <span>托管: PM2</span></div>
                </div>
                <CodeBlock code={botCode} language="python" title="bot.py" filename="bot.py" />
             </div>
          )}

          {activeTab === 'env' && (
             <div className="space-y-2">
                <CodeBlock code={envCode} language="bash" title=".env" filename=".env" />
             </div>
          )}

          {activeTab === 'workflow' && (
            <div className="space-y-2">
               <p className="text-xs text-gray-400">此文件需要放在 <code>.github/workflows/</code> 目录下。</p>
               <CodeBlock code={workflowCode} language="yaml" title="stream.yml" filename="stream.yml" />
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