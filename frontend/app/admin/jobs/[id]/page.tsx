'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Form,
  Input,
  Select,
  Switch,
  Button,
  Typography,
  Space,
  Popconfirm,
  message,
  Card,
  Divider,
  Spin,
  Alert,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  StopOutlined,
  LinkOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { Trash2 } from 'lucide-react';
import { fetchJob, updateJob, deactivateJob, hardDeleteJob } from '@/app/actions/admin';

const { Title, Text } = Typography;

interface AdminJob {
  id: string;
  source: string;
  title: string;
  company: string;
  location: string;
  city: string | null;
  state: string | null;
  country: string | null;
  apply_url: string;
  description_text: string;
  job_category: string | null;
  job_type: string | null;
  work_mode: string | null;
  posted_at: string | null;
  is_active: boolean;
  click_count: number;
  created_at: string | null;
}

const jobTypeOptions = [
  { label: 'Internship', value: 'internship' },
  { label: 'Full Time', value: 'full_time' },
  { label: 'Part Time', value: 'part_time' },
];

const workModeOptions = [
  { label: 'Remote', value: 'remote' },
  { label: 'Hybrid', value: 'hybrid' },
  { label: 'On Site', value: 'on_site' },
];

export default function AdminJobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  const [form] = Form.useForm();
  const [job, setJob] = useState<AdminJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isHardDeleting, setIsHardDeleting] = useState(false);

  // Fetch job data
  useEffect(() => {
    fetchJob(jobId).then((result) => {
      if (result.data) {
        setJob(result.data);
      } else {
        message.error('Failed to load job');
        router.push('/admin/jobs');
      }
      setIsLoading(false);
    });
  }, [jobId, router]);

  // Set form values after job is loaded (and Form is mounted)
  useEffect(() => {
    if (job && !isLoading) {
      form.setFieldsValue(job);
    }
  }, [job, isLoading, form]);

  const handleSave = async (values: Partial<AdminJob>) => {
    setIsSaving(true);
    const result = await updateJob(jobId, values);
    if (result.data) {
      setJob(result.data);
      message.success('Job updated successfully');
    } else {
      message.error(result.error || 'Failed to update job');
    }
    setIsSaving(false);
  };

  const handleDeactivate = async () => {
    setIsDeleting(true);
    const result = await deactivateJob(jobId);
    if (result.success) {
      message.success('Job deactivated successfully');
      router.push('/admin/jobs');
    } else {
      message.error(result.error || 'Failed to deactivate job');
    }
    setIsDeleting(false);
  };

  const handleReactivate = async () => {
    setIsSaving(true);
    const result = await updateJob(jobId, { is_active: true });
    if (result.data) {
      setJob(result.data);
      message.success('Job reactivated successfully');
    } else {
      message.error(result.error || 'Failed to reactivate job');
    }
    setIsSaving(false);
  };

  const handleHardDelete = async () => {
    setIsHardDeleting(true);
    const result = await hardDeleteJob(jobId);
    if (result.success) {
      message.success('Job permanently deleted');
      router.push('/admin/jobs');
    } else {
      message.error(result.error || 'Failed to delete job');
    }
    setIsHardDeleting(false);
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!job) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Title level={4}>Job not found</Title>
        <Button onClick={() => router.push('/admin/jobs')}>Back to Jobs</Button>
      </div>
    );
  }

  return (
    <div>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => router.push('/admin/jobs')}
        style={{ marginBottom: 16 }}
      >
        Back to Jobs
      </Button>

      {!job.is_active && (
        <Alert
          message="This job is inactive and hidden from users."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Title level={3} style={{ margin: 0 }}>
        {job?.title || 'Job Details'}
      </Title>
      {job?.company && (
        <Text type="secondary" style={{ fontSize: 16 }}>
          {job.company}
        </Text>
      )}

      <Form
        form={form}
        layout="vertical"
        style={{ maxWidth: 800, marginTop: 24 }}
        onFinish={handleSave}
      >
        <Card title="Editable Fields" style={{ marginBottom: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Form.Item
              name="title"
              label="Title"
              rules={[{ required: true, message: 'Please enter job title' }]}
            >
              <Input placeholder="Job title" />
            </Form.Item>
            <Form.Item
              name="company"
              label="Company"
              rules={[{ required: true, message: 'Please enter company name' }]}
            >
              <Input placeholder="Company name" />
            </Form.Item>
            <Form.Item name="location" label="Location">
              <Input placeholder="Job location" />
            </Form.Item>
            <Form.Item name="job_category" label="Category">
              <Input placeholder="Job category" />
            </Form.Item>
            <Form.Item name="job_type" label="Job Type">
              <Select options={jobTypeOptions} placeholder="Select job type" allowClear />
            </Form.Item>
            <Form.Item name="work_mode" label="Work Mode">
              <Select options={workModeOptions} placeholder="Select work mode" allowClear />
            </Form.Item>
            <Form.Item
              name="is_active"
              label="Active"
              valuePropName="checked"
              style={{ alignSelf: 'end' }}
            >
              <Switch checkedChildren="Active" unCheckedChildren="Inactive" />
            </Form.Item>
          </div>
        </Card>

        <Card title="Read-only Information" style={{ marginBottom: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <Text type="secondary">Click Count</Text>
              <div>
                <Text strong style={{ fontSize: 18 }}>
                  {job?.click_count ?? 0}
                </Text>
              </div>
            </div>
            <div>
              <Text type="secondary">Posted At</Text>
              <div>
                <Text>
                  {job?.posted_at
                    ? new Date(job.posted_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })
                    : 'N/A'}
                </Text>
              </div>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <Text type="secondary">Apply URL</Text>
              <div>
                {job?.apply_url ? (
                  <a
                    href={job.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                  >
                    <LinkOutlined />
                    {job.apply_url}
                  </a>
                ) : (
                  <Text type="secondary">N/A</Text>
                )}
              </div>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <Text type="secondary">Description</Text>
              <div
                style={{
                  maxHeight: 300,
                  overflow: 'auto',
                  padding: 12,
                  background: '#211F26',
                  borderRadius: 6,
                  border: '1px solid #49454F',
                  marginTop: 8,
                }}
              >
                <Text style={{ whiteSpace: 'pre-wrap' }}>
                  {job?.description_text || 'No description available'}
                </Text>
              </div>
            </div>
          </div>
        </Card>

        <Divider />
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            {job?.is_active ? (
              <Popconfirm
                title="Deactivate this job?"
                description="This will set the job as inactive."
                onConfirm={handleDeactivate}
                okText="Yes, deactivate"
                cancelText="Cancel"
                okButtonProps={{ danger: true, loading: isDeleting }}
              >
                <Button danger icon={<StopOutlined />} loading={isDeleting}>
                  Deactivate Job
                </Button>
              </Popconfirm>
            ) : (
              <>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  loading={isSaving}
                  onClick={handleReactivate}
                >
                  Reactivate Job
                </Button>
                <Popconfirm
                  title="Delete this job permanently?"
                  description="Are you sure? This will permanently delete this job and cannot be undone."
                  onConfirm={handleHardDelete}
                  okText="Yes, delete permanently"
                  cancelText="Cancel"
                  okButtonProps={{ danger: true, loading: isHardDeleting }}
                >
                  <Button danger icon={<Trash2 size={16} />} loading={isHardDeleting}>
                    Delete Permanently
                  </Button>
                </Popconfirm>
              </>
            )}
          </Space>
          <Button type="primary" icon={<SaveOutlined />} loading={isSaving} htmlType="submit">
            Save Changes
          </Button>
        </Space>
      </Form>
    </div>
  );
}
