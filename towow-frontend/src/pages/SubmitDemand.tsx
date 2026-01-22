/**
 * 需求提交页面
 *
 * 用户输入需求，提交后开始AI协商
 *
 * 设计特点:
 * - 渐变背景（紫色调）
 * - 卡片式设计，毛玻璃效果
 * - 流畅动画和即时反馈
 * - 示例需求快速填充
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDemandStore } from '../stores/demandStore';

const SubmitDemand: React.FC = () => {
  const [input, setInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { submitDemand } = useDemandStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await submitDemand(input.trim());
      navigate(`/negotiation/${result.negotiation_id}`);
    } catch (err) {
      console.error('Submit error:', err);
      setError(err instanceof Error ? err.message : '提交失败，请重试');
      setIsSubmitting(false);
    }
  };

  // 预设示例需求
  const examples = [
    '我想在北京组织一场30人的AI技术分享会',
    '找一个懂AI的设计师帮我做产品原型',
    '需要一个会写Python的开发者帮忙优化代码',
  ];

  const handleExampleClick = (example: string) => {
    if (!isSubmitting) {
      setInput(example);
      setError(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Logo/标题 */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-white mb-2 drop-shadow-lg tracking-tight">
            ToWow
          </h1>
          <p className="text-white/80 text-lg">
            AI驱动的智能协作网络
          </p>
        </div>

        {/* 输入卡片 */}
        <div className="bg-white/95 backdrop-blur-lg rounded-2xl shadow-2xl p-8 transform transition-all duration-300 hover:shadow-[0_25px_50px_-12px_rgba(0,0,0,0.25)]">
          <form onSubmit={handleSubmit}>
            <div className="mb-6">
              <label className="block text-gray-700 text-sm font-semibold mb-2">
                描述你的需求
              </label>
              <textarea
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="比如：我想组织一场AI主题的技术分享会..."
                className="w-full h-32 px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none transition-all duration-200 resize-none text-gray-800 placeholder:text-gray-400"
                disabled={isSubmitting}
              />
              {/* 字数统计 */}
              <div className="text-right mt-1 text-xs text-gray-400">
                {input.length} / 2000
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                {error}
              </div>
            )}

            {/* 示例需求 */}
            <div className="mb-6">
              <p className="text-sm text-gray-500 mb-2">或者试试这些示例：</p>
              <div className="flex flex-wrap gap-2">
                {examples.map((example, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleExampleClick(example)}
                    className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-indigo-100 hover:text-indigo-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={isSubmitting}
                  >
                    {example.length > 25 ? `${example.slice(0, 25)}...` : example}
                  </button>
                ))}
              </div>
            </div>

            {/* 提交按钮 */}
            <button
              type="submit"
              disabled={!input.trim() || isSubmitting}
              className={`w-full py-4 rounded-xl font-semibold text-white text-lg transition-all duration-300 transform ${
                isSubmitting
                  ? 'bg-gray-400 cursor-not-allowed'
                  : input.trim()
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 hover:scale-[1.02] active:scale-[0.98] shadow-lg hover:shadow-xl'
                  : 'bg-gray-300 cursor-not-allowed'
              }`}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  正在启动协商...
                </span>
              ) : (
                '开始智能协商'
              )}
            </button>
          </form>
        </div>

        {/* 底部说明 */}
        <div className="mt-8 text-center text-white/70 text-sm">
          <p>提交后，AI将自动匹配合适的协作者并开始协商</p>
        </div>

        {/* 特性介绍 */}
        <div className="mt-12 grid grid-cols-3 gap-4 text-center">
          <div className="text-white/80">
            <div className="text-3xl mb-2">🤖</div>
            <div className="text-sm font-medium">智能理解</div>
            <div className="text-xs text-white/60 mt-1">AI深度解析需求</div>
          </div>
          <div className="text-white/80">
            <div className="text-3xl mb-2">🤝</div>
            <div className="text-sm font-medium">多方协商</div>
            <div className="text-xs text-white/60 mt-1">多Agent协同决策</div>
          </div>
          <div className="text-white/80">
            <div className="text-3xl mb-2">⚡</div>
            <div className="text-sm font-medium">高效执行</div>
            <div className="text-xs text-white/60 mt-1">快速达成共识</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SubmitDemand;
