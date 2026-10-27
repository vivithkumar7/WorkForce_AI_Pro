import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  ArrowUpRight,
  Bell,
  BrainCircuit,
  Building2,
  ClipboardList,
  Clock3,
  FileClock,
  LayoutDashboard,
  LogOut,
  Menu,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  BellRing,
  Banknote,
  CalendarDays,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api, { login } from './api';

const demoTrend = [
  { month: 'May', risk: 31 },
  { month: 'Jun', risk: 34 },
  { month: 'Jul', risk: 29 },
  { month: 'Aug', risk: 39 },
  { month: 'Sep', risk: 36 },
  { month: 'Oct', risk: 42 },
];
const navItems = [
  ['Dashboard', LayoutDashboard],
  ['Employees', Users],
  ['User accounts', UserPlus],
  ['AI Predictions', BrainCircuit],
  ['Departments', Building2],
  ['Alerts', ShieldAlert],
  ['Interventions', ClipboardList],
  ['Attendance', Clock3],
  ['Leave', CalendarDays],
  ['Payroll', Banknote],
  ['Notifications', BellRing],
  ['Audit log', FileClock],
];
const money = (amount) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount || 0);
const payrollMoney = (amount) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount || 0);
const dateTime = (value) => new Date(value).toLocaleString();
const initials = (name) =>
  name
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('');

function Login({ onLogin }) {
  const [email, setEmail] = useState('admin@workforce.local');
  const [password, setPassword] = useState('Admin123!');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(email, password);
      onLogin();
    } catch {
      setError('Login failed. Start the backend and check your credentials.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-art">
        <div className="brand-mark">
          <BrainCircuit size={28} />
          <span>
            <strong>WorkForce <b>AI Pro</b></strong>
            <small>HR Attrition Prediction & Workforce Intelligence Platform</small>
          </span>
        </div>
        <div>
          <div className="eyebrow">PEOPLE INTELLIGENCE PLATFORM</div>
          <h1>
            Predict attrition.
            <br />
            <span>Build stronger teams.</span>
          </h1>
          <p>Bring employee insights, workforce analytics, and thoughtful people decisions together in one secure workspace.</p>
          <div className="login-highlights">
            <span><Users size={15} /> Workforce insights</span>
            <span><ShieldAlert size={15} /> Early risk signals</span>
            <span><Activity size={15} /> People-first decisions</span>
          </div>
        </div>
        <div className="login-foot">PREDICT <i /> ANALYZE <i /> RETAIN <i /> GROW</div>
      </div>
      <form className="login-card" onSubmit={submit}>
        <div className="small-brand">
          <BrainCircuit /> WorkForce AI Pro
        </div>
        <h2>Welcome back</h2>
        <p className="muted">Sign in to continue to your workforce workspace.</p>
        <label htmlFor="login-email">Email address</label>
        <input
          id="login-email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        {error && <p className="error">{error}</p>}
        <button className="primary full" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in to dashboard'}
        </button>
        <div className="demo-note">Demo login: admin@workforce.local / Admin123!</div>
      </form>
    </div>
  );
}

function RiskBadge({ level }) {
  return <span className={`risk-badge risk-${level?.toLowerCase()}`}>{level}</span>;
}

function EmployeeForm({ departments, onCancel, onCreate, onUpdate, employee, busy }) {
  const [form, setForm] = useState(() => employee ? ({
    ...employee,
    department_id: String(employee.department_id),
  }) : ({
    employee_code: '',
    full_name: '',
    email: '',
    job_title: '',
    department_id: departments[0]?.id ?? '',
    tenure_years: 1,
    monthly_income: 40000,
    job_satisfaction: 3,
    work_life_balance: 3,
    overtime: false,
    years_since_promotion: 1,
  }));
  const update = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };
  const submit = (event) => {
    event.preventDefault();
    const payload = {
      ...form,
      department_id: Number(form.department_id),
      tenure_years: Number(form.tenure_years),
      monthly_income: Number(form.monthly_income),
      job_satisfaction: Number(form.job_satisfaction),
      work_life_balance: Number(form.work_life_balance),
      years_since_promotion: Number(form.years_since_promotion),
    };
    if (employee) {
      onUpdate(employee.id, {
        full_name: payload.full_name,
        job_title: payload.job_title,
        department_id: payload.department_id,
        tenure_years: payload.tenure_years,
        monthly_income: payload.monthly_income,
        job_satisfaction: payload.job_satisfaction,
        work_life_balance: payload.work_life_balance,
        overtime: payload.overtime,
        years_since_promotion: payload.years_since_promotion,
      });
    } else {
      onCreate(payload);
    }
  };

  return (
    <form className="panel employee-form" onSubmit={submit}>
      <div className="panel-heading">
        <div>
          <h3>{employee ? 'Edit employee profile' : 'Add employee'}</h3>
          <p>{employee ? 'Update role, department, and workforce profile details.' : 'Provide profile details to add someone to the active workforce.'}</p>
        </div>
        <button className="secondary small" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
      <div className="form-grid">
        {!employee && <label>
          Employee code
          <input name="employee_code" value={form.employee_code} onChange={update} required />
        </label>}
        <label>
          Full name
          <input name="full_name" value={form.full_name} onChange={update} required />
        </label>
        {!employee && <label>
          Email
          <input name="email" type="email" value={form.email} onChange={update} required />
        </label>}
        <label>
          Job title
          <input name="job_title" value={form.job_title} onChange={update} required />
        </label>
        <label>
          Department
          <select name="department_id" value={form.department_id} onChange={update} required>
            {departments.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Monthly pay
          <input
            name="monthly_income"
            type="number"
            min="0"
            value={form.monthly_income}
            onChange={update}
            required
          />
        </label>
        <label>
          Tenure (years)
          <input
            name="tenure_years"
            type="number"
            min="0"
            max="60"
            step="0.1"
            value={form.tenure_years}
            onChange={update}
            required
          />
        </label>
        <label>
          Satisfaction (1–4)
          <input
            name="job_satisfaction"
            type="number"
            min="1"
            max="4"
            value={form.job_satisfaction}
            onChange={update}
            required
          />
        </label>
        <label>
          Work-life balance (1–4)
          <input
            name="work_life_balance"
            type="number"
            min="1"
            max="4"
            value={form.work_life_balance}
            onChange={update}
            required
          />
        </label>
        <label>
          Years since promotion
          <input
            name="years_since_promotion"
            type="number"
            min="0"
            max="60"
            step="0.1"
            value={form.years_since_promotion}
            onChange={update}
            required
          />
        </label>
        <label className="checkbox-field">
          <input name="overtime" type="checkbox" checked={form.overtime} onChange={update} />
          Overtime flag
        </label>
      </div>
      <div className="form-actions">
        <button className="primary" disabled={busy || departments.length === 0}>
          {busy ? 'Saving…' : employee ? 'Save changes' : 'Save employee'}
        </button>
      </div>
    </form>
  );
}

function EmployeeTable({ employees, onDeactivate, onEdit, onLinkAccount, userAccounts, canManage, busy }) {
  if (employees.length === 0) return <div className="empty-state">No employees match your search.</div>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>EMPLOYEE</th>
            <th>DEPARTMENT</th>
            <th>JOB TITLE</th>
            <th>TENURE</th>
            <th>SATISFACTION</th>
            <th>MONTHLY PAY</th>
            {canManage && <th>ACTIONS</th>}
          </tr>
        </thead>
        <tbody>
          {employees.map((employee, index) => (
            <tr key={employee.id}>
              <td>
                <div className="employee-cell">
                  <div className={`person-avatar avatar-${index % 5}`}>{initials(employee.full_name)}</div>
                  <div>
                    <b>{employee.full_name}</b>
                    <small>{employee.employee_code}</small>
                  </div>
                </div>
              </td>
              <td>
                <span className="dept-label">{employee.department_name}</span>
              </td>
              <td>{employee.job_title}</td>
              <td>{employee.tenure_years} yrs</td>
              <td>{employee.job_satisfaction}/4</td>
              <td className="pay-cell">{money(employee.monthly_income)}</td>
              {canManage && (
                <td>
                  <div className="employee-actions">
                    <button className="text-link" disabled={busy} onClick={() => onEdit(employee)}>
                      Edit
                    </button>
                    {!employee.user_id && (
                      <button
                        className="text-link"
                        disabled={busy}
                        onClick={() => onLinkAccount(employee)}
                      >
                        Link account
                      </button>
                    )}
                    {employee.user_id && <span className="dept-label">Account linked</span>}
                    <button
                      className="text-link danger-link"
                      disabled={busy}
                      onClick={() => onDeactivate(employee)}
                    >
                      Deactivate
                    </button>
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PredictionTable({ predictions }) {
  if (predictions.length === 0) return <div className="empty-state">No predictions yet. Run an AI analysis to get started.</div>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>EMPLOYEE</th>
            <th>DEPARTMENT</th>
            <th>RISK</th>
            <th>RISK BAND</th>
            <th>MODEL SIGNALS</th>
            <th>CREATED</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map((prediction) => (
            <tr key={prediction.id ?? prediction.employee_id}>
              <td>
                <b>{prediction.employee_name}</b>
              </td>
              <td>{prediction.department}</td>
              <td className="pay-cell">{prediction.risk_percent}%</td>
              <td>
                <RiskBadge level={prediction.risk_level} />
              </td>
              <td className="explanation-cell">{prediction.explanation || 'Latest recorded risk score'}</td>
              <td>{dateTime(prediction.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AlertTable({ alerts, interventions, canManage, onStart, busy }) {
  if (alerts.length === 0) return <div className="empty-state">No current high-risk alerts.</div>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>EMPLOYEE</th>
            <th>DEPARTMENT</th>
            <th>RISK</th>
            <th>RECOMMENDED HUMAN REVIEW</th>
            <th>UPDATED</th>
            {canManage && <th>WORKFLOW</th>}
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id}>
              <td>
                <b>{alert.employee_name}</b>
              </td>
              <td>{alert.department}</td>
              <td className="pay-cell">{alert.risk_percent}%</td>
              <td className="explanation-cell">{alert.recommendation}</td>
              <td>{dateTime(alert.created_at)}</td>
              {canManage && (
                <td>
                  {interventions.some(
                    (item) => item.employee_id === alert.employee_id && item.status !== 'Completed',
                  ) ? (
                    <span className="dept-label">Review active</span>
                  ) : (
                    <button className="text-link" disabled={busy} onClick={() => onStart(alert)}>
                      Start review
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InterventionTable({ interventions, canManage, onUpdate, busy }) {
  if (interventions.length === 0) return <div className="empty-state">No interventions have been recorded.</div>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>EMPLOYEE</th>
            <th>DEPARTMENT</th>
            <th>INTERVENTION</th>
            <th>STATUS</th>
            <th>NOTES</th>
            <th>OWNER</th>
            <th>UPDATED</th>
          </tr>
        </thead>
        <tbody>
          {interventions.map((item) => (
            <tr key={item.id}>
              <td><b>{item.employee_name}</b></td>
              <td>{item.department}</td>
              <td>{item.intervention_type}</td>
              <td>
                {canManage ? (
                  <select
                    aria-label={`Status for ${item.employee_name}`}
                    value={item.status}
                    disabled={busy}
                    onChange={(event) => onUpdate(item, event.target.value)}
                  >
                    <option>Open</option>
                    <option>In Progress</option>
                    <option>Completed</option>
                  </select>
                ) : (
                  item.status
                )}
              </td>
              <td className="explanation-cell">{item.notes || '—'}</td>
              <td>{item.created_by}</td>
              <td>{dateTime(item.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AttendanceTable({ records }) {
  if (!records.length) return <div className="empty-state">No attendance has been recorded for this selection.</div>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr><th>EMPLOYEE</th><th>CHECK IN</th><th>CHECK OUT</th><th>HOURS</th><th>OVERTIME</th></tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id}>
              <td><b>{record.employee_name}</b></td>
              <td>{dateTime(record.check_in)}</td>
              <td>{record.check_out ? dateTime(record.check_out) : 'Checked in'}</td>
              <td>{record.worked_hours ?? '—'}</td>
              <td>{record.overtime_hours ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LeaveTable({ requests, canReview, busy, onReview }) {
  if (!requests.length) return <div className="empty-state">No leave requests have been recorded.</div>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr><th>EMPLOYEE</th><th>TYPE</th><th>DATES</th><th>DAYS</th><th>REASON</th><th>STATUS</th>{canReview && <th>REVIEW</th>}</tr>
        </thead>
        <tbody>
          {requests.map((request) => (
            <tr key={request.id}>
              <td><b>{request.employee_name}</b></td>
              <td>{request.leave_type}</td>
              <td>{request.start_date} – {request.end_date}</td>
              <td>{request.calendar_days}</td>
              <td className="explanation-cell">{request.reason}</td>
              <td><span className="dept-label">{request.status}</span></td>
              {canReview && (
                <td>
                  {request.status === 'Pending' ? (
                    <div className="employee-actions">
                      <button className="text-link" disabled={busy} onClick={() => onReview(request, 'Approved')}>Approve</button>
                      <button className="text-link danger-link" disabled={busy} onClick={() => onReview(request, 'Rejected')}>Reject</button>
                    </div>
                  ) : request.reviewer_notes || request.reviewed_by || '—'}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NotificationList({ notifications, onRead, busy }) {
  if (!notifications.length) return <div className="empty-state">You are all caught up.</div>;
  return (
    <div className="notification-list">
      {notifications.map((item) => (
        <article className={`notification-item ${item.is_read ? 'read' : 'unread'}`} key={item.id}>
          <div>
            <b>{item.title}</b>
            <p>{item.message}</p>
            <small>{dateTime(item.created_at)}</small>
          </div>
          {!item.is_read && <button className="text-link" disabled={busy} onClick={() => onRead(item)}>Mark read</button>}
        </article>
      ))}
    </div>
  );
}

function AuditTable({ events }) {
  if (!events.length) return <div className="empty-state">No audit events recorded.</div>;
  return (
    <div className="table-scroll">
      <table>
        <thead><tr><th>WHEN</th><th>ACTOR</th><th>ACTION</th><th>ENTITY</th><th>DETAILS</th></tr></thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{dateTime(event.created_at)}</td>
              <td>{event.actor_name}</td>
              <td><b>{event.action}</b></td>
              <td>{event.entity_type} {event.entity_id ?? ''}</td>
              <td>{event.details || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(Boolean(localStorage.getItem('wf_token')));
  const [active, setActive] = useState('Dashboard');
  const [sidebar, setSidebar] = useState(true);
  const [search, setSearch] = useState('');
  const [summary, setSummary] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [interventions, setInterventions] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [payrollRecords, setPayrollRecords] = useState([]);
  const [payrollAssistant, setPayrollAssistant] = useState(null);
  const [showPayrollAssistant, setShowPayrollAssistant] = useState(false);
  const [payrollQuestion, setPayrollQuestion] = useState('');
  const [payrollAssistantBusy, setPayrollAssistantBusy] = useState(false);
  const [payrollAssistantError, setPayrollAssistantError] = useState('');
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [leavePolicies, setLeavePolicies] = useState([]);
  const [leaveBalance, setLeaveBalance] = useState(null);
  const [employeeProfile, setEmployeeProfile] = useState(null);
  const [userAccounts, setUserAccounts] = useState([]);
  const [managedUsers, setManagedUsers] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [monitoringStatus, setMonitoringStatus] = useState('connecting');
  const [auditEvents, setAuditEvents] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [shiftAssignments, setShiftAssignments] = useState([]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showEmployeeForm, setShowEmployeeForm] = useState(false);
  const [employeeToEdit, setEmployeeToEdit] = useState(null);
  const [employeeToLink, setEmployeeToLink] = useState(null);
  const [linkAccountPassword, setLinkAccountPassword] = useState('');
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');
  const [leaveForm, setLeaveForm] = useState({
    employee_id: '',
    leave_type: 'Annual',
    start_date: '',
    end_date: '',
    reason: '',
  });
  const [shiftForm, setShiftForm] = useState({
    name: '',
    start_time: '09:00',
    end_time: '17:00',
    break_minutes: 0,
  });
  const [assignmentForm, setAssignmentForm] = useState({ employee_id: '', shift_id: '' });
  const [departmentForm, setDepartmentForm] = useState({ name: '', description: '' });
  const [departmentEditingId, setDepartmentEditingId] = useState(null);
  const [policyForm, setPolicyForm] = useState({
    leave_type: 'Annual',
    year: new Date().getFullYear(),
    annual_allowance_days: 20,
  });
  const [policyEditingId, setPolicyEditingId] = useState(null);
  const [managedUserForm, setManagedUserForm] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'EMPLOYEE',
  });
  const [payrollForm, setPayrollForm] = useState(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const lastDay = new Date(year, now.getMonth() + 1, 0).getDate();
    return {
      employee_id: '',
      period_start: `${year}-${month}-01`,
      period_end: `${year}-${month}-${String(lastDay).padStart(2, '0')}`,
      allowances: 0,
      bonus: 0,
      deductions: 0,
    };
  });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const notificationCursor = useRef(0);

  async function askPayrollAssistant(question = '') {
    setPayrollAssistantBusy(true);
    setPayrollAssistantError('');
    try {
      const response = await api.post('/api/payroll/assistant', { question });
      setPayrollAssistant(response.data);
    } catch (requestError) {
      setPayrollAssistantError(
        requestError.response?.data?.detail || 'Could not load payroll insights.',
      );
    } finally {
      setPayrollAssistantBusy(false);
    }
  }

  function togglePayrollAssistant() {
    const shouldOpen = !showPayrollAssistant;
    setShowPayrollAssistant(shouldOpen);
    if (shouldOpen) askPayrollAssistant();
  }

  async function load() {
    setLoading(true);
    setError('');
    try {
      const meResponse = await api.get('/api/auth/me');
      const role = meResponse.data.role;
      const canViewHrOps = ['ADMIN', 'HR'].includes(role);
      const canViewWorkforce = ['ADMIN', 'HR', 'MANAGER'].includes(role);
      let linkedProfile = null;
      if (role === 'EMPLOYEE') {
        try {
          const profileResponse = await api.get('/api/me/employee');
          linkedProfile = profileResponse.data;
        } catch (profileError) {
          if (profileError.response?.status !== 403) throw profileError;
        }
      }
      const canUseSelfService = role === 'EMPLOYEE' && linkedProfile !== null;
      const [
        summaryResponse,
        employeeResponse,
        departmentResponse,
        predictionResponse,
        alertResponse,
        interventionResponse,
        attendanceResponse,
        leaveResponse,
        notificationsResponse,
        auditResponse,
        shiftResponse,
        shiftAssignmentsResponse,
        policiesResponse,
        balanceResponse,
        accountsResponse,
        managedUsersResponse,
        payrollResponse,
      ] = await Promise.all([
          canViewWorkforce ? api.get('/api/dashboard/summary') : Promise.resolve({ data: null }),
          canViewWorkforce ? api.get('/api/employees?limit=500') : Promise.resolve({ data: [] }),
          api.get('/api/departments'),
          canViewWorkforce ? api.get('/api/ai/predictions?limit=100') : Promise.resolve({ data: [] }),
          canViewWorkforce ? api.get('/api/ai/alerts') : Promise.resolve({ data: [] }),
          ['ADMIN', 'HR'].includes(meResponse.data.role)
            ? api.get('/api/interventions')
            : Promise.resolve({ data: [] }),
          canViewHrOps || canUseSelfService ? api.get('/api/attendance?limit=200') : Promise.resolve({ data: [] }),
          canViewHrOps || canUseSelfService ? api.get('/api/leaves') : Promise.resolve({ data: [] }),
          api.get('/api/notifications'),
          role === 'ADMIN' ? api.get('/api/audit-logs?limit=200') : Promise.resolve({ data: [] }),
          api.get('/api/shifts'),
          canViewHrOps ? api.get('/api/shifts/assignments') : Promise.resolve({ data: [] }),
          canViewHrOps ? api.get(`/api/leave-policies?year=${new Date().getFullYear()}`) : Promise.resolve({ data: [] }),
          canUseSelfService ? api.get('/api/leaves/balance?leave_type=Annual') : Promise.resolve({ data: null }),
          ['ADMIN', 'HR'].includes(role) ? api.get('/api/users') : Promise.resolve({ data: [] }),
          ['ADMIN', 'HR'].includes(role) ? api.get('/api/admin/users?limit=500') : Promise.resolve({ data: [] }),
          canViewHrOps || canUseSelfService ? api.get('/api/payroll?limit=500') : Promise.resolve({ data: [] }),
        ]);
      setUser(meResponse.data);
      setSummary(summaryResponse.data);
      setEmployees(employeeResponse.data);
      setDepartments(departmentResponse.data);
      setPredictions(predictionResponse.data);
      setAlerts(alertResponse.data);
      setInterventions(interventionResponse.data);
      setAttendance(attendanceResponse.data);
      setPayrollRecords(payrollResponse.data);
      setLeaveRequests(leaveResponse.data);
      setLeavePolicies(policiesResponse.data);
      setLeaveBalance(balanceResponse.data);
      setEmployeeProfile(linkedProfile);
      setUserAccounts(accountsResponse.data);
      setManagedUsers(managedUsersResponse.data);
      setNotifications(notificationsResponse.data);
      notificationCursor.current = Math.max(
        notificationCursor.current,
        notificationsResponse.data.reduce(
          (latestId, notification) => Math.max(latestId, notification.id),
          0,
        ),
      );
      setAuditEvents(auditResponse.data);
      setShifts(shiftResponse.data);
      setShiftAssignments(shiftAssignmentsResponse.data);
      if (role === 'EMPLOYEE' && !['Attendance', 'Leave'].includes(active)) setActive('Notifications');
      if (!selectedEmployeeId && employeeResponse.data.length) {
        setSelectedEmployeeId(String(employeeResponse.data[0].id));
        setLeaveForm((current) => ({ ...current, employee_id: String(employeeResponse.data[0].id) }));
        setAssignmentForm((current) => ({ ...current, employee_id: String(employeeResponse.data[0].id) }));
        setPayrollForm((current) => ({ ...current, employee_id: String(employeeResponse.data[0].id) }));
      }
    } catch (requestError) {
      if (requestError.response?.status === 401) {
        localStorage.removeItem('wf_token');
        setAuthed(false);
      } else {
        setError('Could not load data. Ensure the FastAPI server is running and seed.py has been executed.');
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authed) load();
  }, [authed]);

  useEffect(() => {
    if (!authed || !user?.id) return undefined;

    const controller = new AbortController();
    let retryTimeout;
    let retryDelay = 1000;

    async function connectToNotificationStream() {
      while (!controller.signal.aborted) {
        setMonitoringStatus('connecting');
        try {
          const token = localStorage.getItem('wf_token');
          const response = await fetch(
            `${api.defaults.baseURL}/api/notifications/stream?after_id=${notificationCursor.current}`,
            {
              headers: {
                Authorization: `Bearer ${token}`,
                Accept: 'text/event-stream',
              },
              signal: controller.signal,
            },
          );
          if (response.status === 401) {
            localStorage.removeItem('wf_token');
            setAuthed(false);
            return;
          }
          if (!response.ok || !response.body) {
            setMonitoringStatus('unavailable');
            return;
          }

          setMonitoringStatus('live');
          retryDelay = 1000;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (!controller.signal.aborted) {
            const { done, value } = await reader.read();
            if (done) throw new Error('Notification stream closed.');
            buffer += decoder.decode(value, { stream: true });

            let boundary = buffer.indexOf('\n\n');
            while (boundary !== -1) {
              const event = buffer.slice(0, boundary);
              buffer = buffer.slice(boundary + 2);
              const data = event
                .split(/\r?\n/)
                .filter((line) => line.startsWith('data:'))
                .map((line) => line.slice(5).trimStart())
                .join('\n');
              if (data) {
                const incoming = JSON.parse(data);
                if (!Array.isArray(incoming)) {
                  throw new Error('Invalid notification stream payload.');
                }
                if (incoming.length) {
                  notificationCursor.current = incoming.reduce(
                    (latestId, notification) => Math.max(latestId, notification.id),
                    notificationCursor.current,
                  );
                  setNotifications((current) => {
                    const existingIds = new Set(current.map((item) => item.id));
                    return [...incoming.filter((item) => !existingIds.has(item.id)), ...current]
                      .sort((left, right) => right.id - left.id)
                      .slice(0, 100);
                  });
                  if (['ADMIN', 'HR', 'MANAGER'].includes(user?.role)) {
                    try {
                      const [summaryResponse, alertResponse, predictionResponse] = await Promise.all([
                        api.get('/api/dashboard/summary'),
                        api.get('/api/ai/alerts'),
                        api.get('/api/ai/predictions?limit=100'),
                      ]);
                      setSummary(summaryResponse.data);
                      setAlerts(alertResponse.data);
                      setPredictions(predictionResponse.data);
                    } catch (refreshError) {
                      setError(
                        refreshError.response?.data?.detail
                          || 'A live alert arrived, but workforce insights could not be refreshed.',
                      );
                    }
                  }
                }
              }
              boundary = buffer.indexOf('\n\n');
            }
          }
        } catch (streamError) {
          if (controller.signal.aborted) break;
          setMonitoringStatus('reconnecting');
          await new Promise((resolve) => {
            retryTimeout = window.setTimeout(resolve, retryDelay);
          });
          retryDelay = Math.min(retryDelay * 2, 15000);
        }
      }
    }

    connectToNotificationStream();
    return () => {
      controller.abort();
      window.clearTimeout(retryTimeout);
    };
  }, [authed, user?.id]);

  const filteredEmployees = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return employees;
    return employees.filter((employee) =>
      [
        employee.full_name,
        employee.email,
        employee.employee_code,
        employee.job_title,
        employee.department_name,
      ]
        .join(' ')
        .toLowerCase()
        .includes(term),
    );
  }, [employees, search]);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  const canManage = ['ADMIN', 'HR'].includes(user?.role);
  const canPredict = ['ADMIN', 'HR', 'MANAGER'].includes(user?.role);
  const visibleNavItems = navItems.filter(([name]) =>
    (user?.role !== 'EMPLOYEE' || ['Attendance', 'Leave', 'Payroll', 'Notifications'].includes(name))
    && (name !== 'User accounts' || canManage)
    && (name !== 'Audit log' || user?.role === 'ADMIN')
    && (name !== 'Interventions' || canManage)
    && (!['Attendance', 'Leave'].includes(name) || canManage || user?.role === 'EMPLOYEE'),
  );
  const kpis = [
    { title: 'Total employees', value: summary?.total_employees ?? '—', sub: 'Active workforce', icon: Users, color: 'blue' },
    { title: 'High-risk employees', value: summary?.high_risk_employees ?? '—', sub: 'Needs human review', icon: ShieldAlert, color: 'rose' },
    { title: 'Average risk score', value: summary ? `${summary.average_attrition_risk}%` : '—', sub: 'Latest score per active employee', icon: Activity, color: 'violet' },
    { title: 'Departments', value: summary?.departments ?? '—', sub: 'Across the organization', icon: Building2, color: 'amber' },
    { title: 'Check-ins today', value: summary?.attendance_check_ins_today ?? '—', sub: `${summary?.attendance_open_sessions_today ?? 0} sessions still open`, icon: Clock3, color: 'blue' },
    { title: 'Approved leave today', value: summary?.approved_leave_today ?? '—', sub: `${summary?.pending_leave_requests ?? 0} requests pending`, icon: CalendarDays, color: 'amber' },
    ...(canManage ? [
      { title: 'Payroll this month', value: summary?.payroll_records_this_month ?? 0, sub: 'Generated records', icon: Banknote, color: 'blue' },
      { title: 'Net payroll total', value: payrollMoney(summary?.payroll_net_total_this_month), sub: 'Current calendar month', icon: Banknote, color: 'violet' },
    ] : []),
  ];

  async function runPredictions() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const response = await api.post('/api/ai/predict');
      setNotice(
        `Risk scores refreshed for ${response.data.processed_count} employees; ${response.data.high_risk_count} need human review.`,
      );
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Prediction request failed. Check your role and backend logs.');
    } finally {
      setBusy(false);
    }
  }

  async function createEmployee(payload) {
    setBusy(true);
    setError('');
    try {
      await api.post('/api/employees', payload);
      setShowEmployeeForm(false);
      setNotice('Employee profile created.');
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not create employee profile.');
    } finally {
      setBusy(false);
    }
  }

  async function updateEmployee(employeeId, payload) {
    setBusy(true);
    setError('');
    try {
      await api.put(`/api/employees/${employeeId}`, payload);
      setShowEmployeeForm(false);
      setEmployeeToEdit(null);
      setNotice('Employee profile updated and risk score refreshed.');
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update employee profile.');
    } finally {
      setBusy(false);
    }
  }

  function linkEmployeeAccount(employee) {
    setEmployeeToLink(employee);
    setLinkAccountPassword('');
    setError('');
    setNotice('');
  }

  async function submitEmployeeAccountLink(event) {
    event.preventDefault();
    if (!employeeToLink) return;
    const employee = employeeToLink;
    const account = userAccounts.find((item) =>
      !item.is_linked && item.email.toLowerCase() === employee.email.toLowerCase(),
    );
    if (!account && !linkAccountPassword) {
      setError('Enter a temporary password to create this employee account.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      let accountId = account?.id;
      if (!accountId) {
        const createdAccount = await api.post('/api/admin/users', {
          email: employee.email,
          full_name: employee.full_name,
          password: linkAccountPassword,
          role: 'EMPLOYEE',
        });
        accountId = createdAccount.data.id;
      }
      await api.put(`/api/employees/${employee.id}/account`, { user_id: accountId });
      setNotice(`Account linked for ${employee.full_name}.`);
      setEmployeeToLink(null);
      setLinkAccountPassword('');
      await load();
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail
        || 'Could not link the account. If account creation succeeded, refresh the page and retry linking.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function createManagedUser(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.post('/api/admin/users', managedUserForm);
      setManagedUserForm({
        email: '',
        full_name: '',
        password: '',
        role: 'EMPLOYEE',
      });
      setNotice('User account created.');
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not create user account.');
    } finally {
      setBusy(false);
    }
  }

  async function updateManagedUser(account, changes) {
    setBusy(true);
    setError('');
    try {
      await api.patch(`/api/admin/users/${account.id}`, changes);
      setNotice(`Account updated for ${account.full_name}.`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update user account.');
    } finally {
      setBusy(false);
    }
  }

  async function resetManagedUserPassword(account) {
    const password = window.prompt(
      `Enter a temporary password for ${account.full_name} (12+ characters with upper/lowercase, number, and symbol):`,
    );
    if (password === null) return;
    setBusy(true);
    setError('');
    try {
      await api.post(`/api/admin/users/${account.id}/reset-password`, { password });
      setNotice(`Password reset for ${account.full_name}. Share the temporary password securely.`);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not reset the account password.');
    } finally {
      setBusy(false);
    }
  }

  async function saveDepartment(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (departmentEditingId) {
        await api.put(`/api/departments/${departmentEditingId}`, departmentForm);
        setNotice('Department updated.');
      } else {
        await api.post('/api/departments', departmentForm);
        setNotice('Department created.');
      }
      setDepartmentEditingId(null);
      setDepartmentForm({ name: '', description: '' });
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not save department.');
    } finally {
      setBusy(false);
    }
  }

  async function deleteDepartment(department) {
    if (!window.confirm(`Delete ${department.name}? Departments with employees cannot be deleted.`)) return;
    setBusy(true);
    setError('');
    try {
      await api.delete(`/api/departments/${department.id}`);
      setNotice(`${department.name} was deleted.`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not delete department.');
    } finally {
      setBusy(false);
    }
  }

  async function deactivateEmployee(employee) {
    if (!window.confirm(`Deactivate ${employee.full_name}?`)) return;
    setBusy(true);
    setError('');
    try {
      await api.delete(`/api/employees/${employee.id}`);
      setNotice(`${employee.full_name} was deactivated.`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not deactivate employee.');
    } finally {
      setBusy(false);
    }
  }

  async function attendanceAction(action) {
    if (canManage && !selectedEmployeeId) return;
    setBusy(true);
    setError('');
    try {
      const payload = canManage ? { employee_id: Number(selectedEmployeeId) } : {};
      await api.post(`/api/attendance/${action}`, payload);
      setNotice(action === 'check-in' ? 'Attendance check-in recorded.' : 'Attendance check-out recorded.');
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not record attendance.');
    } finally {
      setBusy(false);
    }
  }

  async function createLeaveRequest(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.post('/api/leaves', {
        leave_type: leaveForm.leave_type,
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        reason: leaveForm.reason,
        ...(canManage
          ? { employee_id: Number(leaveForm.employee_id || selectedEmployeeId) }
          : {}),
      });
      setLeaveForm((current) => ({ ...current, reason: '' }));
      setNotice('Leave request submitted for review.');
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not submit leave request.');
    } finally {
      setBusy(false);
    }
  }

  async function generatePayroll(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.post('/api/payroll', {
        ...payrollForm,
        employee_id: Number(payrollForm.employee_id),
        allowances: Number(payrollForm.allowances),
        bonus: Number(payrollForm.bonus),
        deductions: Number(payrollForm.deductions),
      });
      setNotice('Payroll draft generated.');
      await load();
      await askPayrollAssistant();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not generate payroll.');
    } finally {
      setBusy(false);
    }
  }

  async function updatePayrollStatus(payroll, status) {
    setBusy(true);
    setError('');
    try {
      await api.patch(`/api/payroll/${payroll.id}/status`, { status });
      setNotice(`Payroll for ${payroll.employee_name} marked ${status.toLowerCase()}.`);
      await load();
      await askPayrollAssistant();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update payroll status.');
    } finally {
      setBusy(false);
    }
  }

  async function reviewLeave(request, status) {
    setBusy(true);
    setError('');
    try {
      await api.patch(`/api/leaves/${request.id}`, { status });
      setNotice(`Leave request ${status.toLowerCase()}.`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not review leave request.');
    } finally {
      setBusy(false);
    }
  }

  async function markNotificationRead(notification) {
    setBusy(true);
    setError('');
    try {
      await api.patch(`/api/notifications/${notification.id}/read`);
      setNotifications((current) =>
        current.map((item) => item.id === notification.id ? { ...item, is_read: true } : item),
      );
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update notification.');
    } finally {
      setBusy(false);
    }
  }

  async function saveShift(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.post('/api/shifts', {
        ...shiftForm,
        break_minutes: Number(shiftForm.break_minutes),
      });
      setShiftForm({ name: '', start_time: '09:00', end_time: '17:00', break_minutes: 0 });
      setNotice('Shift created.');
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not create shift.');
    } finally {
      setBusy(false);
    }
  }

  async function saveLeavePolicy(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (policyEditingId) {
        await api.patch(`/api/leave-policies/${policyEditingId}`, {
          annual_allowance_days: Number(policyForm.annual_allowance_days),
        });
        setNotice('Leave policy updated.');
      } else {
        await api.post('/api/leave-policies', {
          ...policyForm,
          year: Number(policyForm.year),
          annual_allowance_days: Number(policyForm.annual_allowance_days),
        });
        setNotice('Leave policy created.');
      }
      setPolicyEditingId(null);
      setPolicyForm({
        leave_type: 'Annual',
        year: new Date().getFullYear(),
        annual_allowance_days: 20,
      });
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not save leave policy.');
    } finally {
      setBusy(false);
    }
  }

  async function assignShift(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.post('/api/shifts/assignments', {
        employee_id: Number(assignmentForm.employee_id),
        shift_id: Number(assignmentForm.shift_id),
      });
      setNotice('Shift assigned.');
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not assign shift.');
    } finally {
      setBusy(false);
    }
  }

  async function startIntervention(alert) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await api.post('/api/interventions', {
        employee_id: alert.employee_id,
        intervention_type: 'Support check-in',
        notes: alert.recommendation,
      });
      setNotice(`A support check-in was opened for ${alert.employee_name}.`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not start the HR review.');
    } finally {
      setBusy(false);
    }
  }

  async function updateIntervention(intervention, status) {
    setBusy(true);
    setError('');
    try {
      await api.patch(`/api/interventions/${intervention.id}`, { status });
      setNotice(`Intervention for ${intervention.employee_name} updated.`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update the intervention.');
    } finally {
      setBusy(false);
    }
  }

  async function downloadReport() {
    setError('');
    try {
      const response = await api.get('/api/reports/workforce.csv', { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'workforce-analytics.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not download the workforce report.');
    }
  }

  async function downloadAttendanceReport() {
    setError('');
    try {
      const response = await api.get('/api/reports/attendance.csv', { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'attendance-report.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not download the attendance report.');
    }
  }

  async function downloadLeaveReport() {
    setError('');
    try {
      const response = await api.get('/api/reports/leaves.csv', { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'leave-report.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not download the leave report.');
    }
  }

  function signOut() {
    localStorage.removeItem('wf_token');
    setAuthed(false);
    setUser(null);
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebar ? '' : 'collapsed'}`}>
        <div className="brand">
          <span className="brand-icon">
            <BrainCircuit size={22} />
          </span>
          {sidebar && (
            <span>
              WorkForce <b>AI Pro</b>
            </span>
          )}
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {visibleNavItems.map(([name, Icon]) => (
            <button
              key={name}
              onClick={() => setActive(name)}
              className={`nav-item ${active === name ? 'selected' : ''}`}
              title={name === 'Payroll' ? 'Payroll with AI Assistant' : name}
            >
              <Icon size={18} />
              {sidebar && <span>{name}</span>}
              {name === 'Payroll' && (
                <span className="nav-ai-badge" aria-label="AI Assistant">
                  <Sparkles size={12} />
                  {sidebar && 'AI'}
                </span>
              )}
              {name === 'Alerts' && alerts.length > 0 && sidebar && (
                <i className="nav-badge">{alerts.length}</i>
              )}
              {name === 'Notifications' && notifications.some((item) => !item.is_read) && sidebar && (
                <i className="nav-badge">{notifications.filter((item) => !item.is_read).length}</i>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card">
            <Bell size={18} />
            {sidebar && (
              <div>
                <b>People-first AI</b>
                <small>Review every signal</small>
              </div>
            )}
          </div>
          <button className="nav-item" onClick={signOut}>
            <LogOut size={18} />
            {sidebar && 'Sign out'}
          </button>
        </div>
      </aside>

      <main className="main-area">
        {active === 'Payroll' && (
          <button
            className="payroll-ai-fab"
            type="button"
              onClick={togglePayrollAssistant}
              aria-label={showPayrollAssistant ? 'Close Payroll AI Assistant' : 'Open Payroll AI Assistant'}
              aria-expanded={showPayrollAssistant}
              title="Payroll AI Assistant"
            >
              {showPayrollAssistant ? <X size={22} /> : <Sparkles size={22} />}
              {!showPayrollAssistant && <span>AI</span>}
            </button>
        )}
        <header className="topbar">
          <div className="top-left">
            <button className="icon-button" onClick={() => setSidebar((value) => !value)} aria-label="Toggle sidebar">
              <Menu size={19} />
            </button>
            <div className="breadcrumb">
              Workspace <span>/</span> <b>{active}</b>
            </div>
          </div>
          <div className="top-actions">
            <div className="search-global">
              <Search size={16} />
              <input
                aria-label="Search employees"
                placeholder="Search employees…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <div className="avatar">{user ? initials(user.full_name) : 'HR'}</div>
            <div className="user-label">
              <b>{user?.full_name || 'WorkForce User'}</b>
              <small>{user?.role || 'Loading profile'}</small>
            </div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">WORKFORCE INTELLIGENCE</div>
              <h1>{active === 'Dashboard' ? `Welcome, ${user?.full_name?.split(' ')[0] || 'Admin'}` : active}</h1>
              <p>Review workforce signals and keep people decisions human-centered.</p>
            </div>
            <div className="heading-actions">
              {canManage && (
                <button className="secondary" onClick={downloadReport}>
                  Download report
                </button>
              )}
              <button className="secondary" onClick={load} disabled={loading}>
                <RefreshCw size={16} /> {loading ? 'Refreshing…' : 'Refresh'}
              </button>
              {canPredict && (
                <button className="primary" onClick={runPredictions} disabled={busy}>
                  <Sparkles size={16} /> {busy ? 'Analyzing…' : 'Run AI analysis'}
                </button>
              )}
            </div>
          </div>

          {error && <div className="alert-error">{error}</div>}
          {notice && <div className="notice">{notice}</div>}

          {active === 'Dashboard' && (
            <>
              <div className="kpi-grid">
                {kpis.map((kpi) => {
                  const Icon = kpi.icon;
                  return (
                    <div className="kpi-card" key={kpi.title}>
                      <div className="kpi-top">
                        <span>{kpi.title}</span>
                        <span className={`kpi-icon ${kpi.color}`}>
                          <Icon size={19} />
                        </span>
                      </div>
                      <div className="kpi-value">{kpi.value}</div>
                      <div className="kpi-sub">
                        <span className="dot" /> {kpi.sub}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="content-grid">
                <section className="panel trend-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Illustrative attrition risk trend</h3>
                      <p>Sample trend only; not calculated from historical workforce records.</p>
                    </div>
                    <span className="select-pill">DEMO DATA</span>
                  </div>
                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={demoTrend} margin={{ top: 12, right: 8, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#6366f1" stopOpacity={0.22} />
                            <stop offset="100%" stopColor="#6366f1" stopOpacity={0.01} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid stroke="#eef0f6" vertical={false} />
                        <XAxis dataKey="month" axisLine={false} tickLine={false} />
                        <YAxis axisLine={false} tickLine={false} unit="%" />
                        <Tooltip />
                        <Area
                          type="monotone"
                          dataKey="risk"
                          name="Illustrative risk index"
                          stroke="#6366f1"
                          strokeWidth={2.5}
                          fill="url(#riskFill)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </section>
                <section className="panel department-panel">
                  <div className="panel-heading">
                    <div>
                      <h3>Department headcount</h3>
                      <p>Active employees by department</p>
                    </div>
                  </div>
                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={summary?.department_headcount || []}
                        layout="vertical"
                        margin={{ top: 4, right: 12, left: 8, bottom: 4 }}
                      >
                        <CartesianGrid stroke="#eef0f6" horizontal={false} />
                        <XAxis type="number" axisLine={false} tickLine={false} />
                        <YAxis type="category" dataKey="department" width={105} axisLine={false} tickLine={false} />
                        <Tooltip />
                        <Bar dataKey="employees" radius={[0, 5, 5, 0]} barSize={18}>
                          {(summary?.department_headcount || []).map((item, index) => (
                            <Cell
                              key={item.department}
                              fill={['#6366f1', '#8b5cf6', '#06b6d4', '#f59e0b', '#fb7185'][index % 5]}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </section>
              </div>
              <section className="panel employees-panel">
                <div className="panel-heading table-heading">
                  <div>
                    <h3>Latest workforce risk scores</h3>
                    <p>Latest saved score for each active employee; high-risk scores require human review.</p>
                  </div>
                  <button className="text-link" onClick={() => setActive('AI Predictions')}>
                    View prediction history <ArrowUpRight size={15} />
                  </button>
                </div>
                <PredictionTable predictions={summary?.recent_predictions || []} />
              </section>
              <div className="panel safety-note">
                Attrition scores are demo estimates, not validated probabilities or employment decisions. Use them
                only as prompts for supportive, confidential human review.
              </div>
            </>
          )}

          {active === 'Employees' && (
            <>
              <section className="panel employees-panel">
                <div className="panel-heading table-heading">
                  <div>
                    <h3>Employee directory</h3>
                    <p>Search and review active workforce profiles.</p>
                  </div>
                  {canManage && (
                    <button className="primary" onClick={() => setShowEmployeeForm((value) => !value)}>
                      <UserPlus size={16} /> {showEmployeeForm ? 'Close form' : 'Add employee'}
                    </button>
                  )}
                </div>
                {employeeToLink && (
                  <form className="account-link-form" onSubmit={submitEmployeeAccountLink}>
                    <div>
                      <h3>Link account for {employeeToLink.full_name}</h3>
                      <p>
                        Work email: <b>{employeeToLink.email}</b>. A matching active EMPLOYEE account
                        will be linked. Otherwise, create one here with a temporary password.
                      </p>
                    </div>
                    {!userAccounts.some((account) => !account.is_linked
                      && account.email.toLowerCase() === employeeToLink.email.toLowerCase()) && (
                      <label>
                        Temporary password
                        <input
                          type="password"
                          autoComplete="new-password"
                          minLength="12"
                          maxLength="128"
                          value={linkAccountPassword}
                          onChange={(event) => setLinkAccountPassword(event.target.value)}
                          placeholder="12+ characters; upper/lowercase, number, symbol"
                          required
                        />
                      </label>
                    )}
                    <div className="employee-actions">
                      <button className="primary" disabled={busy}>
                        {busy ? 'Linking…' : 'Create / link account'}
                      </button>
                      <button
                        className="secondary"
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setEmployeeToLink(null);
                          setLinkAccountPassword('');
                          setError('');
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
                <EmployeeTable
                  employees={filteredEmployees}
                  onDeactivate={deactivateEmployee}
                  onLinkAccount={linkEmployeeAccount}
                  userAccounts={userAccounts}
                  onEdit={(employee) => {
                    setEmployeeToEdit(employee);
                    setShowEmployeeForm(true);
                  }}
                  canManage={canManage}
                  busy={busy}
                />
                <div className="table-footer">
                  Showing <b>{filteredEmployees.length}</b> active employees
                </div>
              </section>
              {showEmployeeForm && (
                <EmployeeForm
                  key={employeeToEdit?.id ?? 'new'}
                  departments={departments}
                  employee={employeeToEdit}
                  onCancel={() => {
                    setShowEmployeeForm(false);
                    setEmployeeToEdit(null);
                  }}
                  onCreate={createEmployee}
                  onUpdate={updateEmployee}
                  busy={busy}
                />
              )}
            </>
          )}

          {active === 'User accounts' && canManage && (
            <>
              <section className="panel employee-form">
                <div className="panel-heading">
                  <div>
                    <h3>Create managed account</h3>
                    <p>Public registration is disabled. HR may create EMPLOYEE accounts; ADMIN may assign any role.</p>
                  </div>
                </div>
                <form className="inline-form" onSubmit={createManagedUser}>
                  <label>Full name
                    <input
                      value={managedUserForm.full_name}
                      onChange={(event) => setManagedUserForm({ ...managedUserForm, full_name: event.target.value })}
                      minLength="2"
                      maxLength="160"
                      required
                    />
                  </label>
                  <label>Email
                    <input
                      type="email"
                      value={managedUserForm.email}
                      onChange={(event) => setManagedUserForm({ ...managedUserForm, email: event.target.value })}
                      required
                    />
                  </label>
                  <label>Temporary password
                    <input
                      type="password"
                      value={managedUserForm.password}
                      onChange={(event) => setManagedUserForm({ ...managedUserForm, password: event.target.value })}
                      minLength="12"
                      maxLength="128"
                      autoComplete="new-password"
                      required
                    />
                  </label>
                  <label>Role
                    <select
                      value={managedUserForm.role}
                      onChange={(event) => setManagedUserForm({ ...managedUserForm, role: event.target.value })}
                    >
                      {user?.role === 'ADMIN' && <option value="ADMIN">ADMIN</option>}
                      {user?.role === 'ADMIN' && <option value="HR">HR</option>}
                      {user?.role === 'ADMIN' && <option value="MANAGER">MANAGER</option>}
                      <option value="EMPLOYEE">EMPLOYEE</option>
                    </select>
                  </label>
                  <button className="primary" disabled={busy}>Create account</button>
                </form>
              </section>
              <section className="panel employees-panel">
                <div className="panel-heading table-heading">
                  <div><h3>Managed user accounts</h3><p>Deactivated accounts cannot sign in. Password resets invalidate issued application sessions.</p></div>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead><tr><th>USER</th><th>EMAIL</th><th>ROLE</th><th>STATUS</th><th>ACTIONS</th></tr></thead>
                    <tbody>
                      {managedUsers.map((account) => (
                        <tr key={account.id}>
                          <td><b>{account.full_name}</b></td>
                          <td>{account.email}</td>
                          <td>
                            {user?.role === 'ADMIN' ? (
                              <select
                                aria-label={`Role for ${account.email}`}
                                value={account.role}
                                disabled={busy}
                                onChange={(event) => updateManagedUser(account, { role: event.target.value })}
                              >
                                <option value="ADMIN">ADMIN</option>
                                <option value="HR">HR</option>
                                <option value="MANAGER">MANAGER</option>
                                <option value="EMPLOYEE">EMPLOYEE</option>
                              </select>
                            ) : account.role}
                          </td>
                          <td><span className={`status ${account.is_active ? 'active' : 'inactive'}`}>{account.is_active ? 'Active' : 'Inactive'}</span></td>
                          <td>
                            {user?.role === 'ADMIN' && (
                              <div className="employee-actions">
                                <button className="text-link" disabled={busy} onClick={() => resetManagedUserPassword(account)}>Reset password</button>
                                <button
                                  className="text-link"
                                  disabled={busy || account.id === user.id}
                                  onClick={() => updateManagedUser(account, { is_active: !account.is_active })}
                                >
                                  {account.is_active ? 'Deactivate' : 'Activate'}
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {active === 'AI Predictions' && (
            <section className="panel employees-panel">
              <div className="panel-heading table-heading">
                <div>
                  <h3>Prediction history</h3>
                  <p>Most recent saved model signals, with the latest 100 entries shown.</p>
                </div>
              </div>
              <PredictionTable predictions={predictions} />
            </section>
          )}

          {active === 'Alerts' && (
            <section className="panel employees-panel">
              <div className="panel-heading table-heading">
                <div>
                  <h3>Current high-risk alerts</h3>
                  <p>Only each active employee’s latest score is used to determine current alert status.</p>
                </div>
              </div>
              <AlertTable
                alerts={alerts}
                interventions={interventions}
                canManage={canManage}
                onStart={startIntervention}
                busy={busy}
              />
            </section>
          )}

          {active === 'Interventions' && (
            <section className="panel employees-panel">
              <div className="panel-heading table-heading">
                <div>
                  <h3>HR intervention workflow</h3>
                  <p>Track supportive human follow-ups for employees flagged for review.</p>
                </div>
              </div>
              <InterventionTable
                interventions={interventions}
                canManage={canManage}
                onUpdate={updateIntervention}
                busy={busy}
              />
            </section>
          )}

          {active === 'Attendance' && (
            <>
              <section className="panel employees-panel">
                <div className="panel-heading table-heading">
                  <div>
                    <h3>Attendance & shift management</h3>
                    <p>Overtime is calculated against the assigned shift duration after the configured break.</p>
                  </div>
                  <div className="inline-controls">
                    {canManage && (
                      <select aria-label="Attendance employee" value={selectedEmployeeId} onChange={(event) => setSelectedEmployeeId(event.target.value)}>
                        {employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.full_name}</option>)}
                      </select>
                    )}
                    {(canManage || employeeProfile) && (
                      <>
                        <button className="primary" disabled={busy || (canManage && !selectedEmployeeId)} onClick={() => attendanceAction('check-in')}>Check in</button>
                        <button className="secondary" disabled={busy || (canManage && !selectedEmployeeId)} onClick={() => attendanceAction('check-out')}>Check out</button>
                      </>
                    )}
                    {canManage && <button className="secondary" onClick={downloadAttendanceReport}>Export CSV</button>}
                  </div>
                </div>
                {user?.role === 'EMPLOYEE' && !employeeProfile ? (
                  <div className="empty-state">Your account is not linked to an employee profile yet. Ask HR to link an account with your work email.</div>
                ) : <AttendanceTable records={attendance} />}
              </section>
              {canManage && (
                <section className="panel employee-form">
                  <div className="panel-heading">
                    <div><h3>Shift setup</h3><p>Create a shift and assign it to an active employee.</p></div>
                  </div>
                  <form onSubmit={saveShift} className="inline-form">
                    <label>Shift name<input value={shiftForm.name} onChange={(event) => setShiftForm({ ...shiftForm, name: event.target.value })} required /></label>
                    <label>Start<input type="time" value={shiftForm.start_time} onChange={(event) => setShiftForm({ ...shiftForm, start_time: event.target.value })} required /></label>
                    <label>End<input type="time" value={shiftForm.end_time} onChange={(event) => setShiftForm({ ...shiftForm, end_time: event.target.value })} required /></label>
                    <label>Break minutes<input type="number" min="0" max="240" value={shiftForm.break_minutes} onChange={(event) => setShiftForm({ ...shiftForm, break_minutes: event.target.value })} /></label>
                    <button className="primary" disabled={busy}>Create shift</button>
                  </form>
                  <form onSubmit={assignShift} className="inline-form">
                    <label>Employee
                      <select value={assignmentForm.employee_id || selectedEmployeeId} onChange={(event) => setAssignmentForm({ ...assignmentForm, employee_id: event.target.value })} required>
                        {employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.full_name}</option>)}
                      </select>
                    </label>
                    <label>Shift
                      <select value={assignmentForm.shift_id} onChange={(event) => setAssignmentForm({ ...assignmentForm, shift_id: event.target.value })} required>
                        <option value="">Select shift</option>
                        {shifts.map((shift) => <option key={shift.id} value={shift.id}>{shift.name} ({shift.start_time}–{shift.end_time})</option>)}
                      </select>
                    </label>
                    <button className="secondary" disabled={busy || !shifts.length}>Assign shift</button>
                  </form>
                  <div className="table-footer">{shiftAssignments.length} current assignment(s) recorded.</div>
                </section>
              )}
            </>
          )}

          {active === 'Leave' && (
            <>
              {canManage && (
                <section className="panel employee-form">
                  <div className="panel-heading">
                    <div><h3>Leave policy</h3><p>Configure inclusive calendar-day allowance by leave type and year.</p></div>
                  </div>
                  <form className="inline-form" onSubmit={saveLeavePolicy}>
                    <label>Leave type<input value={policyForm.leave_type} onChange={(event) => setPolicyForm({ ...policyForm, leave_type: event.target.value })} minLength="2" maxLength="40" required disabled={Boolean(policyEditingId)} /></label>
                    <label>Year<input type="number" min="2000" max="2100" value={policyForm.year} onChange={(event) => setPolicyForm({ ...policyForm, year: event.target.value })} required disabled={Boolean(policyEditingId)} /></label>
                    <label>Annual days<input type="number" min="0" max="366" value={policyForm.annual_allowance_days} onChange={(event) => setPolicyForm({ ...policyForm, annual_allowance_days: event.target.value })} required /></label>
                    <button className="primary" disabled={busy}>{policyEditingId ? 'Save policy' : 'Add policy'}</button>
                    {policyEditingId && <button className="secondary" type="button" onClick={() => { setPolicyEditingId(null); setPolicyForm({ leave_type: 'Annual', year: new Date().getFullYear(), annual_allowance_days: 20 }); }}>Cancel</button>}
                  </form>
                  <div className="table-scroll">
                    <table>
                      <thead><tr><th>LEAVE TYPE</th><th>YEAR</th><th>ALLOWANCE</th><th>STATUS</th><th /></tr></thead>
                      <tbody>
                        {leavePolicies.map((policy) => (
                          <tr key={policy.id}>
                            <td>{policy.leave_type}</td>
                            <td>{policy.year}</td>
                            <td>{policy.annual_allowance_days} days</td>
                            <td>{policy.is_active ? 'Active' : 'Inactive'}</td>
                            <td><button className="text-link" onClick={() => { setPolicyEditingId(policy.id); setPolicyForm({ leave_type: policy.leave_type, year: policy.year, annual_allowance_days: policy.annual_allowance_days }); }}>Edit</button></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
              {(canManage || (user?.role === 'EMPLOYEE' && employeeProfile)) && (
                <form className="panel employee-form" onSubmit={createLeaveRequest}>
                  <div className="panel-heading">
                    <div><h3>Submit leave request</h3><p>Requests are stored for HR review; duration uses inclusive calendar days.</p></div>
                  </div>
                  <div className="inline-form">
                    {canManage && <label>Employee
                      <select value={leaveForm.employee_id || selectedEmployeeId} onChange={(event) => setLeaveForm({ ...leaveForm, employee_id: event.target.value })} required>
                        {employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.full_name}</option>)}
                      </select>
                    </label>}
                    <label>Leave type<input value={leaveForm.leave_type} onChange={(event) => setLeaveForm({ ...leaveForm, leave_type: event.target.value })} required /></label>
                    <label>Start date<input type="date" value={leaveForm.start_date} onChange={(event) => setLeaveForm({ ...leaveForm, start_date: event.target.value })} required /></label>
                    <label>End date<input type="date" value={leaveForm.end_date} onChange={(event) => setLeaveForm({ ...leaveForm, end_date: event.target.value })} required /></label>
                    <label>Reason<input value={leaveForm.reason} onChange={(event) => setLeaveForm({ ...leaveForm, reason: event.target.value })} minLength="3" maxLength="1000" required /></label>
                    <button
                      className="primary"
                      disabled={busy || (canManage ? !employees.length : !employeeProfile)}
                    >
                      Submit request
                    </button>
                  </div>
                </form>
              )}
              {user?.role === 'EMPLOYEE' && !employeeProfile && (
                <div className="panel safety-note">Your account is not linked to an employee profile yet. Ask HR to link an account with your work email before submitting leave.</div>
              )}
              {leaveBalance && (
                <div className="panel safety-note">
                  Annual leave balance for {leaveBalance.year}: {leaveBalance.approved_days_used} used of {leaveBalance.annual_allowance_days} days; {leaveBalance.remaining_days} remaining.
                </div>
              )}
              <section className="panel employees-panel">
                <div className="panel-heading table-heading">
                  <div><h3>Leave requests</h3><p>HR/Admin can approve or reject pending requests.</p></div>
                  {canManage && <button className="secondary" onClick={downloadLeaveReport}>Export leave CSV</button>}
                </div>
                <LeaveTable requests={leaveRequests} canReview={canManage} busy={busy} onReview={reviewLeave} />
              </section>
            </>
          )}

          {active === 'Payroll' && (
            <>
              {showPayrollAssistant && <section className="panel ai-payroll-panel" id="payroll-ai-assistant">
                <div className="panel-heading ai-payroll-heading">
                  <div>
                    <h3><Sparkles size={17} /> AI Payroll Assistant</h3>
                    <p>Understand payroll totals and review unusual entries for the selected period.</p>
                  </div>
                  <div className="ai-payroll-heading-actions">
                    {payrollAssistant?.period_start && (
                      <span className="ai-period">
                        {new Date(`${payrollAssistant.period_start}T00:00:00`).toLocaleDateString(undefined, { year: 'numeric', month: 'long' })}
                      </span>
                    )}
                    <button
                      className="ai-payroll-close"
                      type="button"
                      onClick={() => setShowPayrollAssistant(false)}
                      aria-label="Close Payroll AI Assistant"
                    >
                      <X size={17} />
                    </button>
                  </div>
                </div>
                <div className="ai-payroll-disclaimer">
                  Rule-based, explainable assistance—not a generative AI model. It never changes payroll; HR must verify flagged items before approval.
                </div>
                {payrollAssistantBusy && <p className="muted">Preparing payroll insights…</p>}
                {payrollAssistantError && <p className="error">{payrollAssistantError}</p>}
                {payrollAssistant && (
                  <>
                    <div className="ai-payroll-metrics">
                      <div><span>Net payroll</span><strong>{payrollMoney(payrollAssistant.totals.net_pay)}</strong></div>
                      <div><span>Gross payroll</span><strong>{payrollMoney(payrollAssistant.totals.gross_pay)}</strong></div>
                      <div><span>Deductions</span><strong>{payrollMoney(payrollAssistant.totals.deductions)}</strong></div>
                      <div><span>Records</span><strong>{payrollAssistant.record_count}</strong></div>
                    </div>
                    <div className="ai-payroll-answer">
                      <Sparkles size={16} />
                      <p>{payrollAssistant.answer}</p>
                    </div>
                    {payrollAssistant.alerts.length > 0 ? (
                      <div className="ai-payroll-alerts">
                        <strong>{payrollAssistant.alerts.length} item(s) to review</strong>
                        {payrollAssistant.alerts.slice(0, 5).map((alert) => (
                          <p key={`${alert.payroll_id}-${alert.category}`}>
                            <b>{alert.employee_name}: {alert.category}.</b> {alert.message}
                          </p>
                        ))}
                      </div>
                    ) : (
                      <p className="ai-payroll-clear">No explainable payroll checks were triggered for this period.</p>
                    )}
                  </>
                )}
                <form
                  className="ai-payroll-question"
                  onSubmit={(event) => {
                    event.preventDefault();
                    askPayrollAssistant(payrollQuestion);
                  }}
                >
                  <input
                    id="payroll-ai-question"
                    aria-label="Ask the payroll assistant"
                    value={payrollQuestion}
                    onChange={(event) => setPayrollQuestion(event.target.value)}
                    placeholder="Ask about payroll totals, bonuses, deductions, or record count"
                    maxLength={500}
                  />
                  <button className="primary" disabled={payrollAssistantBusy || !payrollAssistant}>
                    Ask assistant
                  </button>
                </form>
              </section>}
              {canManage && (
                <form className="panel employee-form" onSubmit={generatePayroll}>
                  <div className="panel-heading">
                    <div>
                      <h3>Generate monthly payroll</h3>
                      <p>Draft calculation uses monthly salary + allowances + bonus − deductions. No statutory taxes are calculated.</p>
                    </div>
                  </div>
                  <div className="inline-form">
                    <label>Employee
                      <select
                        value={payrollForm.employee_id}
                        onChange={(event) => setPayrollForm({ ...payrollForm, employee_id: event.target.value })}
                        required
                      >
                        <option value="">Select employee</option>
                        {employees.map((employee) => (
                          <option key={employee.id} value={employee.id}>
                            {employee.full_name} — {payrollMoney(employee.monthly_income)} base
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>Payroll month
                      <input
                        type="month"
                        value={payrollForm.period_start.slice(0, 7)}
                        onChange={(event) => {
                          const [year, month] = event.target.value.split('-').map(Number);
                          if (!year || !month) return;
                          const periodStart = `${event.target.value}-01`;
                          const lastDay = new Date(year, month, 0).getDate();
                          const periodEnd = `${event.target.value}-${String(lastDay).padStart(2, '0')}`;
                          setPayrollForm({ ...payrollForm, period_start: periodStart, period_end: periodEnd });
                        }}
                        required
                      />
                    </label>
                    <label>Allowances<input type="number" min="0" step="0.01" value={payrollForm.allowances} onChange={(event) => setPayrollForm({ ...payrollForm, allowances: event.target.value })} required /></label>
                    <label>Bonus<input type="number" min="0" step="0.01" value={payrollForm.bonus} onChange={(event) => setPayrollForm({ ...payrollForm, bonus: event.target.value })} required /></label>
                    <label>Deductions<input type="number" min="0" step="0.01" value={payrollForm.deductions} onChange={(event) => setPayrollForm({ ...payrollForm, deductions: event.target.value })} required /></label>
                    <button className="primary" disabled={busy || !employees.length}>Generate draft</button>
                  </div>
                </form>
              )}
              {!canManage && user?.role === 'EMPLOYEE' && !employeeProfile && (
                <div className="panel safety-note">Your account is not linked to an employee profile. Ask HR to link your work account to view payslips.</div>
              )}
              <section className="panel employees-panel">
                <div className="panel-heading table-heading">
                  <div>
                    <h3>{canManage ? 'Payroll records' : 'My payslips'}</h3>
                    <p>{canManage ? 'Review salary breakdowns and move records from Draft to Approved to Paid.' : 'Only paid payroll records are available here.'}</p>
                  </div>
                </div>
                {payrollRecords.length === 0 ? (
                  <div className="empty-state">{canManage ? 'No payroll records yet. Generate a monthly draft to begin.' : 'No paid payslips are available yet.'}</div>
                ) : (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          {canManage && <th>EMPLOYEE</th>}
                          <th>PERIOD</th><th>BASE SALARY</th><th>ALLOWANCES</th><th>BONUS</th><th>DEDUCTIONS</th><th>NET PAY</th><th>STATUS</th>
                          {canManage && <th>ACTION</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {payrollRecords.map((payroll) => (
                          <tr key={payroll.id}>
                            {canManage && <td>{payroll.employee_name}<small className="table-subtext">{payroll.employee_code}</small></td>}
                            <td>{new Date(`${payroll.period_start}T00:00:00`).toLocaleDateString(undefined, { year: 'numeric', month: 'long' })}</td>
                            <td>{payrollMoney(payroll.base_salary)}</td>
                            <td>{payrollMoney(payroll.allowances)}</td>
                            <td>{payrollMoney(payroll.bonus)}</td>
                            <td>{payrollMoney(payroll.deductions)}</td>
                            <td><b>{payrollMoney(payroll.net_pay)}</b></td>
                            <td><span className={`status-pill ${payroll.status.toLowerCase()}`}>{payroll.status}</span></td>
                            {canManage && (
                              <td>
                                {payroll.status === 'Draft' && <button className="text-link" disabled={busy} onClick={() => updatePayrollStatus(payroll, 'Approved')}>Approve</button>}
                                {payroll.status === 'Approved' && <button className="text-link" disabled={busy} onClick={() => updatePayrollStatus(payroll, 'Paid')}>Mark paid</button>}
                                {payroll.status === 'Paid' && <span className="muted">Complete</span>}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          )}

          {active === 'Notifications' && (
            <section className="panel employees-panel">
              <div className="panel-heading table-heading">
                <div>
                  <h3>Notifications</h3>
                  <p>
                    Personal alerts with read/unread tracking.
                    {' '}
                    {monitoringStatus === 'live'
                      ? 'Live updates connected.'
                      : monitoringStatus === 'reconnecting'
                        ? 'Reconnecting to live updates…'
                        : monitoringStatus === 'unavailable'
                          ? 'Live updates are unavailable.'
                          : 'Connecting to live updates…'}
                  </p>
                </div>
              </div>
              <NotificationList notifications={notifications} onRead={markNotificationRead} busy={busy} />
            </section>
          )}

          {active === 'Audit log' && user?.role === 'ADMIN' && (
            <section className="panel employees-panel">
              <div className="panel-heading table-heading">
                <div><h3>System audit log</h3><p>Administrative record of employee, department, prediction, attendance, leave, shift, and intervention changes.</p></div>
              </div>
              <AuditTable events={auditEvents} />
            </section>
          )}

          {active === 'Departments' && (
            <section className="panel employees-panel">
              <div className="panel-heading table-heading">
                <div>
                  <h3>Departments</h3>
                  <p>Manage departments and active workforce distribution.</p>
                </div>
              </div>
              {canManage && (
                <form className="inline-form department-form" onSubmit={saveDepartment}>
                  <label>Name<input value={departmentForm.name} onChange={(event) => setDepartmentForm({ ...departmentForm, name: event.target.value })} required minLength="2" maxLength="100" /></label>
                  <label>Description<input value={departmentForm.description} onChange={(event) => setDepartmentForm({ ...departmentForm, description: event.target.value })} maxLength="255" /></label>
                  <button className="primary" disabled={busy}>{departmentEditingId ? 'Save department' : 'Add department'}</button>
                  {departmentEditingId && <button className="secondary" type="button" onClick={() => { setDepartmentEditingId(null); setDepartmentForm({ name: '', description: '' }); }}>Cancel edit</button>}
                </form>
              )}
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>DEPARTMENT</th>
                      <th>DESCRIPTION</th>
                      <th>ACTIVE HEADCOUNT</th>
                      {canManage && <th>ACTIONS</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {departments.map((department) => (
                      <tr key={department.id}>
                        <td>
                          <b>{department.name}</b>
                        </td>
                        <td>{department.description || '—'}</td>
                        <td>{summary?.department_headcount?.find((row) => row.department === department.name)?.employees || 0}</td>
                        {canManage && (
                          <td>
                            <div className="employee-actions">
                              <button className="text-link" onClick={() => { setDepartmentEditingId(department.id); setDepartmentForm({ name: department.name, description: department.description || '' }); }}>Edit</button>
                              <button className="text-link danger-link" disabled={busy} onClick={() => deleteDepartment(department)}>Delete</button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
