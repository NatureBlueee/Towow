import React, { useState } from 'react';
import {
  Card,
  Input,
  Button,
  Form,
  Typography,
  Space,
  message,
  Collapse,
  InputNumber,
  Switch,
} from 'antd';
import { SendOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { demandApi } from '../../api/demand';
import { useDemandStore } from '../../stores/demandStore';
import { useEventStore } from '../../stores/eventStore';
import type { DemandSubmitRequest } from '../../types';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

export const DemandSubmitPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { isSubmitting, setSubmitting, setSubmitError, setParsedDemand } = useDemandStore();
  const { setNegotiationId, setParticipants, setStatus, reset: resetEventStore } = useEventStore();

  const handleSubmit = async (values: {
    user_input: string;
    location?: string;
    budget_min?: number;
    budget_max?: number;
    time_flexible?: boolean;
  }) => {
    setSubmitting(true);
    setSubmitError(null);
    resetEventStore();

    try {
      const request: DemandSubmitRequest = {
        user_input: values.user_input,
        context: {},
      };

      if (values.location) {
        request.context!.location = values.location;
      }

      if (values.budget_min || values.budget_max) {
        request.context!.budget_range = {
          min: values.budget_min,
          max: values.budget_max,
          currency: 'CNY',
        };
      }

      if (values.time_flexible !== undefined) {
        request.context!.time_constraints = {
          flexible: values.time_flexible,
        };
      }

      const response = await demandApi.submit(request);

      setNegotiationId(response.negotiation_id);
      setStatus(response.status);
      setParticipants(response.initial_participants);
      setParsedDemand(response.parsed_demand);

      message.success('需求提交成功，正在开始协商...');
      navigate(`/negotiations/${response.negotiation_id}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '提交失败，请重试';
      setSubmitError(errorMessage);
      message.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Title level={2}>提交您的需求</Title>
      <Paragraph type="secondary">
        用自然语言描述您的需求，AI 代理将帮您寻找最佳方案并进行协商。
      </Paragraph>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ time_flexible: true }}
        >
          <Form.Item
            name="user_input"
            label="需求描述"
            rules={[
              { required: true, message: '请描述您的需求' },
              { min: 10, message: '请提供更详细的描述（至少10个字符）' },
            ]}
          >
            <TextArea
              rows={4}
              placeholder="例如：我想预订下周六晚上7点在上海外滩附近的法餐厅，2人用餐，预算500-800元..."
              maxLength={2000}
              showCount
            />
          </Form.Item>

          <Space style={{ marginBottom: 16 }}>
            <Button
              type="link"
              icon={<SettingOutlined />}
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? '隐藏高级选项' : '显示高级选项'}
            </Button>
          </Space>

          {showAdvanced && (
            <Collapse
              defaultActiveKey={['context']}
              items={[
                {
                  key: 'context',
                  label: '补充信息（可选）',
                  children: (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Form.Item name="location" label="地点">
                        <Input placeholder="例如：上海、北京朝阳区" />
                      </Form.Item>

                      <Space>
                        <Form.Item name="budget_min" label="预算下限">
                          <InputNumber
                            min={0}
                            placeholder="最低"
                            style={{ width: 150 }}
                            prefix="¥"
                          />
                        </Form.Item>
                        <Form.Item name="budget_max" label="预算上限">
                          <InputNumber
                            min={0}
                            placeholder="最高"
                            style={{ width: 150 }}
                            prefix="¥"
                          />
                        </Form.Item>
                      </Space>

                      <Form.Item
                        name="time_flexible"
                        label="时间灵活"
                        valuePropName="checked"
                      >
                        <Switch checkedChildren="是" unCheckedChildren="否" />
                      </Form.Item>
                    </Space>
                  ),
                },
              ]}
            />
          )}

          <Form.Item style={{ marginTop: 24 }}>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SendOutlined />}
              loading={isSubmitting}
              size="large"
              block
            >
              提交需求并开始协商
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default DemandSubmitPage;
