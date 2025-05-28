/// <reference types="cypress" />
/// <reference types="cypress-real-events" />
import 'cypress-axe';
import 'cypress-real-events/support';

describe('ChatWidget Accessibility', () => {
  beforeEach(() => {
    cy.visit('/');
    cy.injectAxe();
  });

  it('should have no detectable a11y violations after popup interaction', () => {
    // Trigger citation popup
    cy.get('textarea[aria-label="Chat input"]').type('refund policy{enter}');
    cy.get('[data-cy^="citation-marker-"]').first().click();
    cy.checkA11y('[role="dialog"]');
    // Close popup and check main widget
    cy.get('[role="dialog"] button[aria-label="Close citation popup"]').click();
    cy.checkA11y('.max-w-md');
  });

  it('popup should trap focus and be keyboard accessible', () => {
    cy.get('textarea[aria-label="Chat input"]').type('subscription cancel{enter}');
    cy.get('[data-cy^="citation-marker-"]').first().focus().type('{enter}');
    cy.get('[role="dialog"]').should('exist');
    // Tab should cycle inside popup
    cy.get('body').realPress('Tab');
    cy.focused().should('have.attr', 'aria-label', 'Close citation popup');
    cy.get('[role="dialog"]').type('{esc}');
    cy.get('[role="dialog"]').should('not.exist');
  });

  it('should meet color contrast requirements', () => {
    cy.checkA11y('.max-w-md', {
      runOnly: ['color-contrast'],
    });
  });
});
