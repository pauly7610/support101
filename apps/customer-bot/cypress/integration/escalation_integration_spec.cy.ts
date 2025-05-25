/// <reference types="cypress" />
import 'cypress-axe';

describe('Escalation Analytics Integration', () => {
  it('End-to-end: escalation triggers backend and dashboard update', () => {
    cy.visit('/');
    cy.injectAxe();
    // 1. Send escalation message
    cy.intercept('POST', '**/report_escalation').as('reportEscalation');
    const msg = 'This is urgent, please help!';
    cy.get('textarea[aria-label="Chat input"]').type(`${msg}{enter}`);
    cy.wait('@reportEscalation').its('response.statusCode').should('eq', 200);
    // 2. Go to analytics dashboard
    cy.visit('/analytics');
    cy.injectAxe();n    // 3. Confirm escalation appears in dashboard
    cy.contains(msg).should('exist');
    cy.get('.max-w-lg').contains('Total Escalations:').should('exist');
    // 4. Confirm chart bar for today exists
    const today = new Date().toLocaleDateString();
    cy.get('.max-w-lg').contains(today);
    // 5. Accessibility check
    cy.checkA11y('.max-w-lg');
  });
});
