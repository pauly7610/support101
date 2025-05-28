/// <reference types="cypress" />

// Test chat history persistence using IndexedDB

describe('ChatWidget Persistence', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('persists chat messages after reload', () => {
    cy.get('textarea[aria-label="Chat input"]').type('Persistent message{enter}');
    cy.get('[data-cy="user-message"]').contains('Persistent message').should('exist');
    cy.reload();
    cy.get('[data-cy="user-message"]').contains('Persistent message').should('exist');
  });
});
