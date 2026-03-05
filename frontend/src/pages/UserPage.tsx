import React, { useState, useEffect, useRef } from 'react';
import {
  Steps,
  Upload,
  Button,
  InputNumber,
  Select,
  Card,
  Progress,
  Typography,
  Space,
  Alert,
  Divider,
  Tag,
  message,
  Form,
  Input,
} from 'antd';
import {
  UploadOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import {
  parseQuestionnaire,
  startGeneration,
  getGenerationStatus,
  getDownloadUrl,
  type Questionnaire,
} from '../api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

type Step = 'upload' | 'config' | 'generating' | 'done';

interface GenerationStatus {
  status: string;
  done: number;
  total: number;
  download_token?: string;
  error?: string;
}

const UserPage: React.FC = () => {
  const [step, setStep] = useState<Step>('upload');
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [textInput, setTextInput] = useState('');
  const [taskId, setTaskId] = useState('');
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [sampleCount, setSampleCount] = useState(100);
  const [exportFormat, setExportFormat] = useState<'csv' | 'excel'>('csv');
  const [loading, setLoading] = useState(false);
  const [genTaskId, setGenTaskId] = useState('');
  const [genStatus, setGenStatus] = useState<GenerationStatus | null>(null);
  const [downloadToken, setDownloadToken] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stepIndex = { upload: 0, config: 1, generating: 2, done: 3 }[step];

  // Cleanup poll on unmount
  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const handleParse = async () => {
    const file = fileList[0]?.originFileObj;
    if (!file && !textInput.trim()) {
      message.warning('请上传文件或输入问卷文本');
      return;
    }
    setLoading(true);
    try {
      const result = await parseQuestionnaire(file, textInput || undefined);
      setTaskId(result.task_id);
      setQuestionnaire(result.questionnaire);
      setStep('config');
      message.success('问卷解析成功');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '解析失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    if (!taskId) return;
    setLoading(true);
    try {
      const result = await startGeneration({ task_id: taskId, sample_count: sampleCount, export_format: exportFormat });
      setGenTaskId(result.gen_task_id);
      setStep('generating');
      setGenStatus({ status: 'pending', done: 0, total: sampleCount });
      // Start polling
      pollRef.current = setInterval(async () => {
        try {
          const s = await getGenerationStatus(result.gen_task_id);
          setGenStatus(s);
          if (s.status === 'completed') {
            clearInterval(pollRef.current!);
            setDownloadToken(s.download_token || '');
            setStep('done');
          } else if (s.status === 'failed') {
            clearInterval(pollRef.current!);
            message.error('生成失败：' + (s.error || '未知错误'));
          }
        } catch { /* ignore poll errors */ }
      }, 2000);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '启动失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const url = getDownloadUrl(downloadToken);
    window.open(url, '_blank');
  };

  const percent = genStatus ? Math.round((genStatus.done / Math.max(genStatus.total, 1)) * 100) : 0;

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '40px 16px' }}>
      <Title level={2} style={{ textAlign: 'center', marginBottom: 8 }}>
        AI 问卷数据生成系统
      </Title>
      <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 32 }}>
        上传问卷 → AI 解析 → 生成模拟回答 → 下载 CSV/Excel
      </Paragraph>

      <Steps
        current={stepIndex}
        items={[
          { title: '上传问卷' },
          { title: '配置参数' },
          { title: '生成数据' },
          { title: '下载结果' },
        ]}
        style={{ marginBottom: 32 }}
      />

      {/* Step 0: Upload */}
      {step === 'upload' && (
        <Card title="上传问卷">
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Text strong>方式一：上传文件（PDF / 图片 / TXT）</Text>
              <div style={{ marginTop: 8 }}>
                <Upload
                  fileList={fileList}
                  beforeUpload={() => false}
                  onChange={({ fileList: fl }) => setFileList(fl.slice(-1))}
                  accept=".pdf,.txt,.jpg,.jpeg,.png,.webp"
                  maxCount={1}
                >
                  <Button icon={<UploadOutlined />}>选择文件</Button>
                </Upload>
              </div>
            </div>
            <Divider>或</Divider>
            <div>
              <Text strong>方式二：直接粘贴问卷文本</Text>
              <Input.TextArea
                rows={8}
                placeholder="请将问卷内容粘贴到这里..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                style={{ marginTop: 8 }}
              />
            </div>
            <Button
              type="primary"
              size="large"
              loading={loading}
              onClick={handleParse}
              block
            >
              解析问卷
            </Button>
          </Space>
        </Card>
      )}

      {/* Step 1: Config */}
      {step === 'config' && questionnaire && (
        <Card title="配置生成参数">
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Text strong>解析结果：</Text>
              <div style={{ marginTop: 8, background: '#fafafa', padding: 12, borderRadius: 6 }}>
                <Text>问卷标题：{questionnaire.title || '（未识别）'}</Text>
                <br />
                <Text>共 {questionnaire.questions.length} 道题目</Text>
                <div style={{ marginTop: 8 }}>
                  {questionnaire.questions.slice(0, 5).map((q) => (
                    <div key={q.id} style={{ marginBottom: 4 }}>
                      <Tag color="blue">{q.type}</Tag>
                      <Text ellipsis style={{ maxWidth: 500 }}>{q.text}</Text>
                    </div>
                  ))}
                  {questionnaire.questions.length > 5 && (
                    <Text type="secondary">... 及其他 {questionnaire.questions.length - 5} 题</Text>
                  )}
                </div>
              </div>
            </div>
            <Form layout="inline">
              <Form.Item label="生成样本数">
                <InputNumber
                  min={10}
                  max={2000}
                  value={sampleCount}
                  onChange={(v) => setSampleCount(v || 100)}
                />
              </Form.Item>
              <Form.Item label="导出格式">
                <Select value={exportFormat} onChange={setExportFormat} style={{ width: 100 }}>
                  <Option value="csv">CSV</Option>
                  <Option value="excel">Excel</Option>
                </Select>
              </Form.Item>
            </Form>
            <Space>
              <Button onClick={() => setStep('upload')}>返回</Button>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={loading}
                onClick={handleStart}
              >
                开始生成
              </Button>
            </Space>
          </Space>
        </Card>
      )}

      {/* Step 2: Generating */}
      {step === 'generating' && genStatus && (
        <Card title="正在生成数据">
          <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }} size="large">
            <Progress
              percent={percent}
              status={genStatus.status === 'failed' ? 'exception' : 'active'}
              strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
            />
            <Text>
              已完成：{genStatus.done} / {genStatus.total} 条
            </Text>
            <Text type="secondary">AI 正在模拟不同人群的问卷回答，请稍候...</Text>
            {genStatus.status === 'failed' && (
              <Alert type="error" message={'生成失败：' + (genStatus.error || '')} />
            )}
          </Space>
        </Card>
      )}

      {/* Step 3: Done */}
      {step === 'done' && (
        <Card>
          <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }} size="large">
            <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a' }} />
            <Title level={3}>生成完成！</Title>
            <Text type="secondary">数据已生成 {sampleCount} 条问卷回答，点击下方按钮下载（链接为一次性，请及时保存）。</Text>
            <Button
              type="primary"
              size="large"
              icon={<DownloadOutlined />}
              onClick={handleDownload}
            >
              下载结果（{exportFormat.toUpperCase()}）
            </Button>
            <Button
              onClick={() => {
                setStep('upload');
                setFileList([]);
                setTextInput('');
                setQuestionnaire(null);
                setTaskId('');
                setGenTaskId('');
                setGenStatus(null);
                setDownloadToken('');
              }}
            >
              重新生成
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default UserPage;
