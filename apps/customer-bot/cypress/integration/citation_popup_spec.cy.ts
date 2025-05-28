/// <reference types="cypress" />

// Tests for citation markers and popup in the Customer Chat Widget

describe('ChatWidget Citation Popup', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('shows citation markers on agent message and opens popup with details', () => {
    // Send a message that will trigger agent reply with citations
    cy.get('textarea[aria-label="Chat input"]').type('refund policy{enter}');

    // Wait for agent message with citations
    cy.get('[data-cy="agent-message"]').should('exist');
    cy.get('[data-cy^="citation-marker-"]').should('have.length.at.least', 1);

    // Click the first citation marker
    cy.get('[data-cy="citation-marker-0"]').click();

    // Popup should show excerpt, confidence, last updated, and a source link
    cy.get('[role="dialog"]').should('exist');
    cy.contains('Source Excerpt').should('exist');
    cy.get('blockquote').should('exist');
    cy.contains('Confidence:').should('exist');
    cy.contains('Last Updated:').should('exist');
    cy.get('a').contains('View full source').should('have.attr', 'href');

    // Popup should be keyboard accessible (Escape closes)
    cy.get('[role="dialog"]').type('{esc}');
    cy.get('[role="dialog"]').should('not.exist');
  });

  it('can navigate citation markers and popup by keyboard', () => {
    cy.get('textarea[aria-label="Chat input"]').type('subscription cancel{enter}');
    cy.get('[data-cy^="citation-marker-"]').first().focus().type('{enter}');
    cy.get('[role="dialog"]').should('exist');
    cy.get('[role="dialog"] button[aria-label="Close citation popup"]').focus().type('{enter}');
    cy.get('[role="dialog"]').should('not.exist');
  });

  it('shows no citation markers if agent reply has no citations', () => {
    // Send a message that will not trigger citations
    cy.get('textarea[aria-label="Chat input"]').type('hello agent{enter}');
    cy.get('[data-cy="agent-message"]').should('exist');
    cy.get('[data-cy^="citation-marker-"]').should('not.exist');
  });
});
