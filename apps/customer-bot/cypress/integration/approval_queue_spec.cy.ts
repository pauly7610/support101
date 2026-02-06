/// <reference types="cypress" />

const mockRequests = [
  {
    request_id: 'req-001',
    agent_id: 'agent-abc12345',
    tenant_id: 'tenant-xyz',
    request_type: 'response_review',
    priority: 'critical',
    status: 'pending',
    question: 'How do I reset my enterprise SSO password?',
    context: { ticket_id: 'T-1001', channel: 'email' },
    options: ['approve', 'reject', 'edit'],
    created_at: new Date(Date.now() - 300000).toISOString(),
    assigned_to: null,
    sla_deadline: new Date(Date.now() + 600000).toISOString(),
  },
  {
    request_id: 'req-002',
    agent_id: 'agent-def67890',
    tenant_id: 'tenant-xyz',
    request_type: 'escalation_review',
    priority: 'high',
    status: 'assigned',
    question: 'Customer requesting full account deletion under GDPR',
    context: { ticket_id: 'T-1002', channel: 'chat' },
    options: ['approve', 'reject'],
    created_at: new Date(Date.now() - 900000).toISOString(),
    assigned_to: 'current-user',
    sla_deadline: new Date(Date.now() - 60000).toISOString(),
  },
  {
    request_id: 'req-003',
    agent_id: 'agent-ghi11111',
    tenant_id: 'tenant-xyz',
    request_type: 'response_review',
    priority: 'low',
    status: 'pending',
    question: 'General FAQ about pricing tiers',
    context: { ticket_id: 'T-1003', channel: 'slack' },
    options: ['approve', 'reject'],
    created_at: new Date(Date.now() - 1800000).toISOString(),
    assigned_to: null,
    sla_deadline: null,
  },
];

describe('Approval Queue', () => {
  beforeEach(() => {
    cy.intercept('GET', '**/v1/hitl/queue*', {
      statusCode: 200,
      body: mockRequests,
    }).as('fetchQueue');

    cy.intercept('POST', '**/v1/hitl/queue/*/assign', {
      statusCode: 200,
      body: { status: 'assigned' },
    }).as('assignRequest');

    cy.intercept('POST', '**/v1/hitl/queue/*/respond', {
      statusCode: 200,
      body: { status: 'completed' },
    }).as('respondRequest');
  });

  it('renders the approval queue header and stats', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[aria-label="Approval Queue"]').should('exist');
    cy.contains('Approval Queue').should('be.visible');
    cy.contains('Pending Review').should('be.visible');
    cy.contains('Assigned to You').should('be.visible');
    cy.contains('SLA Breached').should('be.visible');
  });

  it('displays correct stats counts', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    // 2 pending, 1 assigned to current-user, 1 SLA breached (req-002)
    cy.get('.text-blue-600').contains('2');
    cy.get('.text-purple-600').contains('1');
    cy.get('.text-red-600').contains('1');
  });

  it('renders request list with priority and status badges', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[role="list"]').should('exist');
    cy.get('[role="listitem"]').should('have.length', 3);
    cy.get('[role="status"]').should('have.length.at.least', 6);
  });

  it('shows SLA breached indicator for overdue requests', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[aria-label="SLA breached"]').should('exist');
  });

  it('filters by pending tab', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[role="tab"]').contains('Pending').click();
    cy.get('[role="listitem"]').should('have.length', 2);
  });

  it('filters by My Assignments tab', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[role="tab"]').contains('My Assignments').click();
    cy.get('[role="listitem"]').should('have.length', 1);
    cy.contains('GDPR').should('be.visible');
  });

  it('claims a pending request', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[aria-label*="Assign request req-001"]').first().click();
    cy.wait('@assignRequest').its('request.body').should('deep.include', {
      reviewer_id: 'current-user',
    });
  });

  it('opens review panel for assigned request', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[role="tab"]').contains('My Assignments').click();
    cy.get('[aria-label*="Review request req-002"]').click();
    cy.contains('Context').should('be.visible');
    cy.get('[aria-label="Review notes"]').should('be.visible');
    cy.get('[aria-label="Approve request"]').should('be.visible');
    cy.get('[aria-label="Reject request"]').should('be.visible');
  });

  it('approves a request with notes', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[role="tab"]').contains('My Assignments').click();
    cy.get('[aria-label*="Review request req-002"]').click();
    cy.get('[aria-label="Review notes"]').type('Looks good, approved for GDPR deletion.');
    cy.get('[aria-label="Approve request"]').click();
    cy.wait('@respondRequest').its('request.body').should('deep.include', {
      decision: 'approve',
    });
  });

  it('rejects a request', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[role="tab"]').contains('My Assignments').click();
    cy.get('[aria-label*="Review request req-002"]').click();
    cy.get('[aria-label="Reject request"]').click();
    cy.wait('@respondRequest').its('request.body').should('deep.include', {
      decision: 'reject',
    });
  });

  it('shows empty state when no requests match filter', () => {
    cy.intercept('GET', '**/v1/hitl/queue*', {
      statusCode: 200,
      body: [],
    }).as('fetchEmptyQueue');
    cy.visit('/approval');
    cy.wait('@fetchEmptyQueue');
    cy.contains('No requests matching this filter').should('be.visible');
  });

  it('shows error banner on fetch failure', () => {
    cy.intercept('GET', '**/v1/hitl/queue*', {
      statusCode: 500,
      body: { error: 'Internal server error' },
    }).as('fetchError');
    cy.visit('/approval');
    cy.wait('@fetchError');
    cy.get('[role="alert"]').should('be.visible');
    cy.get('[aria-label="Dismiss error"]').click();
    cy.get('[role="alert"]').should('not.exist');
  });

  it('is keyboard accessible', () => {
    cy.visit('/approval');
    cy.wait('@fetchQueue');
    cy.get('[role="tab"]').first().focus();
    cy.focused().should('have.attr', 'role', 'tab');
    cy.get('[role="tab"]').each(($tab) => {
      cy.wrap($tab).should('have.attr', 'aria-selected');
    });
  });
});
