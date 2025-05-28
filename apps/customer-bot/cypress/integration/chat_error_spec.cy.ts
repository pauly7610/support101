/// <reference types="cypress" />

// Test agent error and retry workflow

describe('ChatWidget Agent Error Handling', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('shows error and allows retry when backend fails', () => {
    // Simulate backend error by intercepting /generate_reply
    cy.intercept('POST', '**/generate_reply', {
      statusCode: 500,
      body: {
        error_type: 'llm_timeout',
        message: 'LLM response exceeded 30s threshold',
        retryable: true,
        documentation: 'https://api.support101/errors#E429',
      },
    }).as('generateReplyError');
    cy.get('textarea[aria-label="Chat input"]').type('Trigger error{enter}');
    cy.wait('@generateReplyError');
    cy.contains('Something went wrong').should('exist');
    cy.contains('Retry').click();
    // Remove intercept to allow success
    cy.intercept('POST', '**/generate_reply').as('generateReply');
    cy.get('textarea[aria-label="Chat input"]').type('Try again{enter}');
    cy.wait('@generateReply');
    cy.contains('Try again').should('exist');
    cy.contains('Something went wrong').should('not.exist');
  });
});
