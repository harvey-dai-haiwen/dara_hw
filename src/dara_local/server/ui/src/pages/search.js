import React, { useState } from 'react';
import styled from 'styled-components';
import Layout from '../components/Layout';
import { Button, Form, Input, Upload, Alert, message, Select, InputNumber } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { navigate } from 'gatsby';

const URL = process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8899/api';

const Container = styled.div`
  font-size: 1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 20px;

  h1 {
    margin-bottom: 24px;
  }

  .form-container {
    width: 100%;
    max-width: 800px;
    background: white;
    padding: 24px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }

  .nav-links {
    margin-bottom: 16px;
    a {
      margin-right: 16px;
      color: #1890ff;
      text-decoration: none;
      &:hover {
        text-decoration: underline;
      }
    }
  }
`;

const DATABASES = ['COD', 'ICSD', 'MP', 'NONE'];

const INSTRUMENT_NAMES = [
  'Aeris-fds-Pixcel1d-Medipix3',
  'synchrotron',
  'LBL-d8-LynxEyeXE',
  'd8-solxe-fds-0600',
  'siemens-d5000-fds1mm',
];

function LocalSearch() {
  const [form] = Form.useForm();
  const [msg, setMsg] = useState(null);
  const [messageApi, contextHolder] = message.useMessage();
  const [submitting, setSubmitting] = useState(false);
  const [database, setDatabase] = useState('COD');

  const onSubmit = async () => {
    try {
      const values = await form.validateFields();
      const formData = new FormData();

      // Add pattern file
      if (values.pattern_file && values.pattern_file.length > 0) {
        formData.append('pattern_file', values.pattern_file[0].originFileObj);
      }

      // Parse and add required elements
      const requiredElems = values.required_elements
        .split(/[\s,]+/)
        .filter(e => e.trim())
        .map(e => e.trim());
      formData.append('required_elements', JSON.stringify(requiredElems));

      // Parse and add exclude elements
      const excludeElems = values.exclude_elements
        ? values.exclude_elements.split(/[\s,]+/).filter(e => e.trim()).map(e => e.trim())
        : [];
      formData.append('exclude_elements', JSON.stringify(excludeElems));

      // Add other fields
      formData.append('database', values.database || 'COD');
      formData.append('user', values.user || 'anonymous');
      formData.append('wavelength', values.wavelength || 'Cu');
      formData.append('instrument_profile', values.instrument_profile || 'Aeris-fds-Pixcel1d-Medipix3');
      formData.append('max_phases', values.max_phases || 500);

      // MP-specific parameters
      if (values.database === 'MP') {
        formData.append('mp_experimental_only', values.mp_experimental_only ? 'true' : 'false');
        formData.append('mp_max_e_above_hull', values.mp_max_e_above_hull || 0.1);
      }

      // Add custom CIF files
      if (values.additional_phases && values.additional_phases.length > 0) {
        values.additional_phases.forEach(file => {
          formData.append('additional_phases', file.originFileObj);
        });
      }

      setMsg(null);
      setSubmitting(true);

      const response = await fetch(`${URL}/search`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.wf_id) {
        messageApi.success('Task submitted to queue!');
        // Navigate to task page
        setTimeout(() => {
          navigate(`/task?task_id=${data.wf_id}`);
        }, 1000);
      } else {
        setMsg(data.detail || data.error || 'Submission failed');
      }
    } catch (error) {
      console.error('Submit error:', error);
      setMsg(error.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const normFile = (e) => {
    if (Array.isArray(e)) {
      return e;
    }
    return e?.fileList;
  };

  return (
    <Layout hasSider={false} title="Local Database Search">
      {contextHolder}
      <Container>
        <div className="nav-links">
          <a href="/task">View Task List</a>
          <a href="/">Original Submit Page</a>
        </div>

        {msg && <Alert message={msg} type="error" showIcon closable style={{ width: '100%', maxWidth: '800px', marginBottom: '16px' }} />}

        <div className="form-container">
          <h1>Local Database Phase Search</h1>
          <p style={{ color: '#666', marginBottom: '24px' }}>
            Search COD, ICSD, or MP databases with chemical system filtering and custom CIF upload support
          </p>

          <Form
            form={form}
            layout="vertical"
            initialValues={{
              database: 'COD',
              user: 'researcher',
              wavelength: 'Cu',
              instrument_profile: 'Aeris-fds-Pixcel1d-Medipix3',
              max_phases: 500,
              mp_experimental_only: false,
              mp_max_e_above_hull: 0.1,
            }}
            onValuesChange={(changed) => {
              if (changed.database) {
                setDatabase(changed.database);
              }
            }}
          >
            <Form.Item
              label="Username"
              name="user"
              rules={[{ required: true, message: 'Please enter a username' }]}
            >
              <Input placeholder="For task tracking" />
            </Form.Item>

            <Form.Item
              label="XRD Pattern File"
              name="pattern_file"
              valuePropName="fileList"
              getValueFromEvent={normFile}
              rules={[{ required: true, message: 'Please upload an XRD file' }]}
            >
              <Upload
                beforeUpload={() => false}
                maxCount={1}
                accept=".xy,.xrdml,.raw,.txt,.xye"
              >
                <Button icon={<UploadOutlined />}>Choose File (.xy, .xrdml, .raw)</Button>
              </Upload>
            </Form.Item>

            <Form.Item
              label="Database Selection"
              name="database"
              rules={[{ required: true }]}
            >
              <Select>
                {DATABASES.map(db => (
                  <Select.Option key={db} value={db}>{db}</Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Required Elements"
              name="required_elements"
              rules={[{ required: true, message: 'Please enter element symbols' }]}
              tooltip="Space or comma separated, e.g.: Y Mo O or Y,Mo,O. Phases containing ONLY these elements (and their subsets) will be included."
            >
              <Input placeholder="e.g.: Y Mo O" />
            </Form.Item>

            <Form.Item
              label="Exclude Elements (Optional)"
              name="exclude_elements"
              tooltip="Phases containing any of these elements will be excluded. Typically not needed - just specify required elements."
            >
              <Input placeholder="e.g.: Pb Cd" />
            </Form.Item>

            {database === 'MP' && (
              <>
                <Form.Item
                  label="Experimental Phases Only"
                  name="mp_experimental_only"
                  valuePropName="checked"
                >
                  <input type="checkbox" />
                  <span style={{ marginLeft: 8 }}>Only include experimentally verified phases</span>
                </Form.Item>

                <Form.Item
                  label="Max Energy Above Hull (eV/atom)"
                  name="mp_max_e_above_hull"
                >
                  <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </>
            )}

            <Form.Item
              label="Wavelength"
              name="wavelength"
            >
              <Input placeholder="Cu, Co, Cr, Fe, Mo or value (Å)" />
            </Form.Item>

            <Form.Item
              label="Instrument Profile"
              name="instrument_profile"
            >
              <Select>
                {INSTRUMENT_NAMES.map(name => (
                  <Select.Option key={name} value={name}>{name}</Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Max Phases"
              name="max_phases"
            >
              <InputNumber min={10} max={5000} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item
              label="Custom CIF Files (Optional)"
              name="additional_phases"
              valuePropName="fileList"
              getValueFromEvent={normFile}
            >
              <Upload
                beforeUpload={() => false}
                multiple
                accept=".cif"
              >
                <Button icon={<UploadOutlined />}>Upload CIF Files</Button>
              </Upload>
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                onClick={onSubmit}
                loading={submitting}
                size="large"
                block
              >
                {submitting ? 'Submitting...' : 'Submit Search Task'}
              </Button>
            </Form.Item>
          </Form>
        </div>
      </Container>
    </Layout>
  );
}

export default LocalSearch;
