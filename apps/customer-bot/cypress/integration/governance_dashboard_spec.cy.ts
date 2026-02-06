/// <reference types="cypress" />

const mockDashboard = {
  agents: { total: 12, active: 8, awaiting_human: 3 },
  hitl: {
    pending: 5,
    assigned: 2,
    completed: 47,
    expired: 1,
    avg_response_time_ms: 4500,
  },
  audit: { total_events: 312, recent_events: 28 },
  tenants: { total: 4, active: 3 },
};

const mockAgents = [
  {
    agent_id: 'agent-abc123456789',
    name: 'Support Triage Agent',
    blueprint: 'triage_agent',
    status: 'running',
    tenant_id: 'tenant-xyz12345',
  },
  {
    agent_id: 'agent-def987654321',
    name: 'Knowledge Manager',
    blueprint: 'knowledge_manager_agent',
    status: 'idle',
    tenant_id: 'tenant-xyz12345',
  },
  {
    agent_id: 'agent-ghi555555555',
    name: 'Compliance Auditor',
    blueprint: 'compliance_auditor_agent',
    status: 'awaiting_human',
    tenant_id: 'tenant-abc99999',
  },
];

const mockAuditLog = [
  {
    event_id: 'evt-001',
    event_type: 'execution_completed',
    agent_id: 'agent-abc123456789',
    tenant_id: 'tenant-xyz12345',
    timestamp: new Date(Date.now() - 120000).toISOString(),
    details: { duration_ms: 1200, tokens_used: 450 },
  },
  {
    event_id: 'evt-002',
    event_type: 'human_feedback_provided',
    agent_id: 'agent-def987654321',
    tenant_id: 'tenant-xyz12345',
    timestamp: new Date(Date.now() - 600000).toISOString(),
    details: { decision: 'approve', reviewer: 'admin-01' },
  },
  {
    event_id: 'evt-003',
    event_type: 'execution_failed',
    agent_id: 'agent-ghi555555555',
    tenant_id: 'tenant-abc99999',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    details: { error: 'LLM timeout', retryable: true },
  },
];

describe('Governance Dashboard', () => {
  beforeEach(() => {
    cy.intercept('GET', '**/v1/governance/dashboard*', {
      statusCode: 200,
      body: mockDashboard,
    }).as('fetchDashboard');

    cy.intercept('GET', '**/v1/governance/agents*', {
      statusCode: 200,
      body: mockAgents,
    }).as('fetchAgents');

    cy.intercept('GET', '**/v1/governance/audit*', {
      statusCode: 200,
      body: mockAuditLog,
    }).as('fetchAudit');
  });

  it('renders the governance dashboard header', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.get('[aria-label="Governance Dashboard"]').should('exist');
    cy.contains('Governance Dashboard').should('be.visible');
    cy.contains('Agent monitoring, compliance, and audit trail').should('be.visible');
  });

  it('displays metric cards with correct values', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.contains('Total Agents').should('be.visible');
    cy.contains('12').should('be.visible');
    cy.contains('8 active').should('be.visible');
    cy.contains('Awaiting Human').should('be.visible');
    cy.contains('3').should('be.visible');
    cy.contains('HITL Pending').should('be.visible');
    cy.contains('Audit Events').should('be.visible');
    cy.contains('312').should('be.visible');
  });

  it('displays average HITL response time', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.contains('Avg HITL Response Time').should('be.visible');
    cy.contains('4.5s').should('be.visible');
    cy.contains('47').should('be.visible'); // resolved
    cy.contains('1').should('be.visible'); // expired
  });

  it('shows SLA compliance status', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    // Overview tab is default
    cy.contains('SLA Compliance').should('be.visible');
    cy.contains('1 SLA violation').should('be.visible');
  });

  it('shows tenant overview on overview tab', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.contains('Tenant Overview').should('be.visible');
    cy.contains('Total Tenants').should('be.visible');
    cy.contains('Active Tenants').should('be.visible');
  });

  it('switches to agents tab and displays agent table', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.get('[role="tab"]').contains('agents').click();
    cy.get('[role="table"]').should('exist');
    cy.contains('Support Triage Agent').should('be.visible');
    cy.contains('Knowledge Manager').should('be.visible');
    cy.contains('Compliance Auditor').should('be.visible');
    cy.contains('triage_agent').should('be.visible');
  });

  it('shows status dots for agents', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.get('[role="tab"]').contains('agents').click();
    cy.get('[aria-label="Status: running"]').should('exist');
    cy.get('[aria-label="Status: idle"]').should('exist');
    cy.get('[aria-label="Status: awaiting_human"]').should('exist');
  });

  it('switches to audit tab and displays audit log', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.get('[role="tab"]').contains('audit').click();
    cy.get('[role="log"]').should('exist');
    cy.contains('execution completed').should('be.visible');
    cy.contains('human feedback provided').should('be.visible');
    cy.contains('execution failed').should('be.visible');
  });

  it('toggles audit event details', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.get('[role="tab"]').contains('audit').click();
    cy.get('[aria-label="Toggle event details"]').first().click();
    cy.get('#detail-evt-001').should('not.have.class', 'hidden');
    cy.get('[aria-label="Toggle event details"]').first().click();
    cy.get('#detail-evt-001').should('have.class', 'hidden');
  });

  it('refresh button re-fetches data', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.get('[aria-label="Refresh dashboard"]').click();
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
  });

  it('shows error banner on API failure and dismisses it', () => {
    cy.intercept('GET', '**/v1/governance/dashboard*', {
      statusCode: 500,
      body: {},
    }).as('fetchDashboardError');
    cy.visit('/governance');
    cy.wait('@fetchDashboardError');
    cy.get('[role="alert"]').should('be.visible');
    cy.get('[aria-label="Dismiss error"]').click();
    cy.get('[role="alert"]').should('not.exist');
  });

  it('shows loading state initially', () => {
    cy.intercept('GET', '**/v1/governance/dashboard*', {
      statusCode: 200,
      body: mockDashboard,
      delay: 2000,
    }).as('slowDashboard');
    cy.visit('/governance');
    cy.contains('Loading governance dashboard...').should('be.visible');
  });

  it('tabs are keyboard accessible', () => {
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchAudit']);
    cy.get('[role="tablist"]').should('exist');
    cy.get('[role="tab"]').each(($tab) => {
      cy.wrap($tab).should('have.attr', 'aria-selected');
    });
  });

  it('shows empty agents state when no agents registered', () => {
    cy.intercept('GET', '**/v1/governance/agents*', {
      statusCode: 200,
      body: [],
    }).as('fetchEmptyAgents');
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchEmptyAgents', '@fetchAudit']);
    cy.get('[role="tab"]').contains('agents').click();
    cy.contains('No agents registered').should('be.visible');
  });

  it('shows empty audit state when no events', () => {
    cy.intercept('GET', '**/v1/governance/audit*', {
      statusCode: 200,
      body: [],
    }).as('fetchEmptyAudit');
    cy.visit('/governance');
    cy.wait(['@fetchDashboard', '@fetchAgents', '@fetchEmptyAudit']);
    cy.get('[role="tab"]').contains('audit').click();
    cy.contains('No audit events').should('be.visible');
  });
});
