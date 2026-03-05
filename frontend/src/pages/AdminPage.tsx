import React, { useState, useEffect } from 'react';
import {
  Layout,
  Menu,
  Card,
  Statistic,
  Table,
  Form,
  Input,
  Button,
  Select,
  Row,
  Col,
  Typography,
  Space,
  Tag,
  Spin,
  Alert,
  message,
  Tabs,
} from 'antd';
import {
  DashboardOutlined,
  FileTextOutlined,
  LineChartOutlined,
  LogoutOutlined,
  DollarOutlined,
  ApiOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import {
  adminLogin,
  getAdminStats,
  getCostTrend,
  getAdminRecords,
  type RecordsParams,
} from '../api';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

// ─────────────────────── Login Form ────────────────────────────────────────

const LoginForm: React.FC<{ onLogin: () => void }> = ({ onLogin }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    setError('');
    try {
      const res = await adminLogin(values.username, values.password);
      localStorage.setItem('admin_token', res.access_token);
      onLogin();
    } catch {
      setError('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card title="管理员登录" style={{ width: 360 }}>
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input prefix={<UserOutlined />} placeholder="admin" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password placeholder="密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
};

// ─────────────────────── Dashboard ─────────────────────────────────────────

interface StatsData {
  call_count: number;
  total_cost: number;
  total_tokens: number;
  unique_users: number;
}

interface TrendPoint {
  date: string;
  cost: number;
  calls: number;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [trendDays, setTrendDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchTrend();
  }, [trendDays]);

  const fetchStats = async () => {
    try {
      const res = await getAdminStats();
      setStats(res.data);
    } catch { /* handled below */ }
    setLoading(false);
  };

  const fetchTrend = async () => {
    try {
      const res = await getCostTrend(trendDays);
      setTrend(res.data || []);
    } catch { /* ignored */ }
  };

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['花费（USD）', '调用次数'] },
    xAxis: { type: 'category', data: trend.map((d) => d.date) },
    yAxis: [
      { type: 'value', name: '花费（USD）' },
      { type: 'value', name: '调用次数' },
    ],
    series: [
      {
        name: '花费（USD）',
        type: 'line',
        smooth: true,
        data: trend.map((d) => d.cost.toFixed(4)),
        itemStyle: { color: '#1677ff' },
      },
      {
        name: '调用次数',
        type: 'bar',
        yAxisIndex: 1,
        data: trend.map((d) => d.calls),
        itemStyle: { color: '#95de64' },
      },
    ],
  };

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="今日调用次数" value={stats?.call_count ?? 0} prefix={<ApiOutlined />} valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="今日花费（USD）" value={stats?.total_cost?.toFixed(4) ?? '0.0000'} prefix={<DollarOutlined />} valueStyle={{ color: '#fa8c16' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="今日 Token 用量" value={stats?.total_tokens ?? 0} prefix={<ThunderboltOutlined />} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="今日活跃用户" value={stats?.unique_users ?? 0} prefix={<UserOutlined />} valueStyle={{ color: '#722ed1' }} />
          </Card>
        </Col>
      </Row>

      <Card
        title="花费趋势"
        extra={
          <Select value={trendDays} onChange={setTrendDays} style={{ width: 100 }}>
            <Option value={7}>近 7 天</Option>
            <Option value={30}>近 30 天</Option>
          </Select>
        }
      >
        <ReactECharts option={trendOption} style={{ height: 300 }} />
      </Card>
    </Space>
  );
};

// ─────────────────────── Records Table ─────────────────────────────────────

const RecordsTable: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<RecordsParams>({});

  useEffect(() => {
    fetchRecords();
  }, [page, filters]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const res = await getAdminRecords({ page, page_size: 20, ...filters });
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch {
      message.error('加载记录失败');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 70 },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      render: (v: string) => (
        <Tag color={v === 'parse_questionnaire' ? 'blue' : 'green'}>{v}</Tag>
      ),
    },
    { title: '用户 ID', dataIndex: 'user_id', ellipsis: true },
    { title: '模型', dataIndex: 'model' },
    { title: '时间', dataIndex: 'timestamp', width: 180 },
    { title: 'Prompt Tokens', dataIndex: 'prompt_tokens' },
    { title: 'Completion Tokens', dataIndex: 'completion_tokens' },
    { title: '花费（USD）', dataIndex: 'cost', render: (v: number) => v?.toFixed(6) },
    {
      title: '状态',
      dataIndex: 'success',
      render: (v: boolean) => <Tag color={v ? 'success' : 'error'}>{v ? '成功' : '失败'}</Tag>,
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small">
        <Form layout="inline" onFinish={(vals) => { setFilters(vals); setPage(1); }}>
          <Form.Item name="task_type" label="任务类型">
            <Select allowClear style={{ width: 180 }} placeholder="全部">
              <Option value="parse_questionnaire">问卷解析</Option>
              <Option value="generate_response">数据生成</Option>
            </Select>
          </Form.Item>
          <Form.Item name="user_id" label="用户 ID">
            <Input placeholder="用户 IP" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="model" label="模型">
            <Input placeholder="模型名称" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">筛选</Button>
          </Form.Item>
        </Form>
      </Card>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
        scroll={{ x: 1000 }}
        size="small"
      />
    </Space>
  );
};

// ─────────────────────── Main AdminPage ────────────────────────────────────

const AdminPage: React.FC = () => {
  const [loggedIn, setLoggedIn] = useState(() => !!localStorage.getItem('admin_token'));
  const [activeKey, setActiveKey] = useState('dashboard');

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    setLoggedIn(false);
  };

  if (!loggedIn) {
    return <LoginForm onLogin={() => setLoggedIn(true)} />;
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={220}>
        <div style={{ color: '#fff', textAlign: 'center', padding: '24px 0 16px', fontWeight: 700, fontSize: 18 }}>
          系统管理
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[activeKey]}
          onClick={({ key }) => setActiveKey(key)}
          items={[
            { key: 'dashboard', icon: <DashboardOutlined />, label: '概览仪表盘' },
            { key: 'records', icon: <FileTextOutlined />, label: '运营记录' },
            { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
          ]}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Text strong style={{ fontSize: 18 }}>AI 问卷数据生成系统 — 管理员后台</Text>
        </Header>
        <Content style={{ margin: 24 }}>
          {activeKey === 'dashboard' && <Dashboard />}
          {activeKey === 'records' && <RecordsTable />}
          {activeKey === 'logout' && (() => { handleLogout(); return null; })()}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AdminPage;
