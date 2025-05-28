/// <reference types="cypress" />

describe('UI Component Coverage', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('renders AnalyticsDashboard and displays charts', () => {
    cy.visit('/analytics');
    cy.get('[data-cy="analytics-dashboard"]').should('exist');
    cy.get('[data-cy="escalation-chart"]').should('exist');
  });

  it('renders ComplianceSettings and toggles options', () => {
    cy.visit('/compliance');
    cy.get('[data-cy="compliance-settings"]').should('exist');
    cy.get('[data-cy="optout-toggle"]').click();
    cy.get('[data-cy="optout-toggle"]').should('have.attr', 'aria-checked');
  });
});
