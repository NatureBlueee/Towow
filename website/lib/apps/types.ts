/**
 * 应用元数据类型定义
 * 用于应用注册表和应用目录页面
 */

export type AppStatus = 'active' | 'beta' | 'coming-soon' | 'archived';

export type AppCategory =
  | 'collaboration'  // 协作类
  | 'matching'       // 匹配类
  | 'negotiation'    // 协商类
  | 'exchange'       // 交换类
  | 'demo';          // 演示类

export interface AppPreview {
  image?: string;      // 预览图片
  video?: string;      // 预览视频
  screenshots?: string[]; // 截图列表
}

export interface AppMetadata {
  id: string;                  // 应用唯一标识
  name: string;                // 应用名称
  nameZh?: string;             // 中文名称（可选）
  description: string;         // 应用描述
  descriptionZh?: string;      // 中文描述（可选）
  icon: string;                // 应用图标（emoji 或 path）
  path: string;                // 应用路径（如 /apps/team-matcher）
  status: AppStatus;           // 应用状态
  category: AppCategory;       // 应用分类
  tags: string[];              // 标签列表
  preview?: AppPreview;        // 预览信息
  featured?: boolean;          // 是否为推荐应用
  createdAt?: string;          // 创建时间
  updatedAt?: string;          // 更新时间
  author?: string;             // 作者
  version?: string;            // 版本号
}

export interface AppCardProps {
  app: AppMetadata;
  onClick?: () => void;
  className?: string;
}

export interface AppGridProps {
  apps: AppMetadata[];
  title?: string;
  emptyMessage?: string;
  columns?: 1 | 2 | 3 | 4;
}
