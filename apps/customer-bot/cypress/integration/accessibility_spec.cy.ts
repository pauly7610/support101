/// <reference types="cypress" />
import 'cypress-axe';

describe('Accessibility Compliance', () => {
  beforeEach(() => {
    cy.visit('/');
    cy.injectAxe();
  });

  it('ChatWidget should have no detectable a11y violations', () => {
    cy.checkA11y('.max-w-md');
  });

  it('AnalyticsDashboard should have no detectable a11y violations', () => {
    cy.visit('/analytics');
    cy.injectAxe();
    cy.checkA11y('.max-w-lg');
  });
});
