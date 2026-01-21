import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface LoadingProps {
  tip?: string;
  size?: 'small' | 'default' | 'large';
  fullScreen?: boolean;
}

export const Loading: React.FC<LoadingProps> = ({
  tip = '加载中...',
  size = 'default',
  fullScreen = false,
}) => {
  const antIcon = <LoadingOutlined spin />;

  if (fullScreen) {
    return (
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          zIndex: 9999,
        }}
      >
        <Spin indicator={antIcon} size={size} tip={tip} />
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 0',
      }}
    >
      <Spin indicator={antIcon} size={size} tip={tip} />
    </div>
  );
};

export default Loading;
